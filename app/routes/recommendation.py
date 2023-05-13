import re, requests
import pandas as pd
import numpy as np
import datetime
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from nltk.corpus import stopwords
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.linalg import svd
from sklearn.metrics.pairwise import cosine_similarity

from config import get_mail_username, get_mail_password, get_mail_server, get_mail_port
from utils.connection import create_neo4j_connection
from model.user import User
from model.media import Media
from model.news import News
from model.category import Category


driver = create_neo4j_connection()

recommendation_bp = Blueprint("recommendation_bp", __name__)


def remove_html_tags(text):
    soup = BeautifulSoup(text, "html.parser")
    stripped_text = soup.get_text()
    return stripped_text


def stemming(text):
    factory = StemmerFactory()
    stemmer = factory.create_stemmer()
    text = stemmer.stem(text)
    return text


def case_folding(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)  # Menghapus tanda baca
    text = text.replace("-", " ")  # Menghapus tanda hubung
    text = re.sub(r"\d+", "", text)  # Menghapus angka
    return text


def remove_stopwords(text):
    stopword_factory = StopWordRemoverFactory()
    stopwords = stopword_factory.get_stop_words()
    text = " ".join([word for word in text.split() if word not in stopwords])
    return text


def preprocess_text(text):
    text = remove_html_tags(text)
    text = stemming(text)
    text = case_folding(text)
    text = remove_stopwords(text)
    return text


@recommendation_bp.route("/gethistory")
def get_history(email):
    email = email
    time_now = datetime.datetime.now().timestamp()
    time_12_hours_ago = (
        # edit jam history
        datetime.datetime.now()
        - datetime.timedelta(hours=24)
    ).timestamp()
    time_now_str = datetime.datetime.fromtimestamp(time_now).strftime(
        "%Y-%m-%d %H:%M:%S.%f"
    )
    time_12_hours_ago_str = datetime.datetime.fromtimestamp(time_12_hours_ago).strftime(
        "%Y-%m-%d %H:%M:%S.%f"
    )
    with driver.session() as session:
        user = User.find_by_email(session, email)
        data = User.find_history_periodly(
            session, email, time_12_hours_ago_str, time_now_str
        )
    if not data:
        return None
    data = pd.DataFrame.from_dict(data)
    data = data[["_id", "original", "title", "content", "image", "date"]]
    data["preprocessed_content"] = data["content"].apply(preprocess_text)
    return data.to_dict("records")


@recommendation_bp.route("/getnews")
def get_news():
    response = requests.get("http://103.59.95.88/api/get/news/10")
    data = response.json()
    if not data:
        return None
    df = pd.DataFrame.from_dict(data)
    df = df[
        ["_id", "original", "title", "content", "image", "date", "kategori", "media"]
    ]
    df["preprocessed_content"] = df["content"].apply(preprocess_text)
    return df.to_dict("records")

def calculate_recommendation(email):
    # email = "naurathirahh@gmail.com"
    history_list = get_history(email)
    if not history_list:
        return None
    else:
        df = get_news()
        if not df:
            return {"message": "No news found"}
        else:
            print("start recommendation")
            recommendation_data = []
            for i in range(0, len(df), 10):
                temp_df = df[i : i + 10]
                for j in range(len(history_list)):
                    concat_df = pd.concat(
                        [
                            pd.DataFrame.from_dict(history_list[j], orient="index").T,
                            pd.DataFrame.from_dict(temp_df),
                        ],
                        ignore_index=True,
                    )
                    concat_df.insert(0, "id", range(1, 1 + len(concat_df)))

                    # Add views column to concat_df
                    concat_df["view"] = 0

                    # Get media data
                    media = get_media()

                    # Add views count to concat_df based on media name
                    for m in media:
                        medianame = m["nama"]
                        concat_df.loc[concat_df["media"] == medianame, "view"] = m[
                            "view"
                        ]

                    # Create the TF-IDF matrix
                    tf = TfidfVectorizer()
                    concat_df["preprocessed_content"].fillna("", inplace=True)
                    # Transform TFIDF to Content
                    tfidf_matrix = tf.fit_transform(concat_df["preprocessed_content"])
                    A = tfidf_matrix.T
                    # SVD & Konversi Matrix Sparse -> Dense
                    U, s, VT = svd(A.todense())
                    V = VT.T
                    # Perkalian Matriks V dan S
                    VS = np.dot(V, np.diag(s))
                    # Cosine similarity matriks VS
                    cosine_similarities = cosine_similarity(VS)
                    results = {}
                    for idx, row in concat_df.iterrows():
                        similar_indices = cosine_similarities[idx].argsort()[:-100:-1]
                        similar_items = [
                            (cosine_similarities[idx][i], concat_df["id"][i])
                            for i in similar_indices
                        ]
                        # First item is the item itself, so remove it.
                        # Each dictionary entry is like: [(1,2), (3,4)], with each tuple being (score, item_id)
                        results[row["id"]] = similar_items[1:]
                    result = {}
                    result["recommendation"] = []
                    recs = results.get(1, [])[:3]
                    for rec in recs:
                        recommendation = {}
                        recommendation["score"] = round(rec[0], 2)
                        index = rec[1] - 1
                        # Get the values of the columns that you need
                        recommendation["id_history"] = str(concat_df.loc[0, "_id"])
                        recommendation["_id"] = str(concat_df.loc[index, "_id"])
                        recommendation["original"] = concat_df.loc[index, "original"]
                        recommendation["title"] = concat_df.loc[index, "title"]
                        recommendation["image"] = concat_df.loc[index, "image"]
                        recommendation["date"] = concat_df.loc[index, "date"]
                        recommendation["kategori"] = concat_df.loc[index, "kategori"]
                        recommendation["media"] = concat_df.loc[index, "media"]
                        recommendation["content"] = concat_df.loc[index, "content"]
                        recommendation["view"] = str(concat_df.loc[index, "view"])
                        result["recommendation"].append(recommendation)
                    recommendation_data.append(result)

                # Combine all recommendation results into one list
                combined_recommendations = []
                for result in recommendation_data:
                    # combined_recommendations["email"] = email
                    combined_recommendations.extend(result["recommendation"])
                    # sort recommendations based on score and then views in descending order
                    combined_recommendations = sorted(
                        combined_recommendations,
                        key=lambda x: (x["score"], x["date"], x["view"]),
                        reverse=(True),
                    )

                # Create a dictionary to store unique recommendations based on article ID
                unique_recommendations = {}

                # Iterate through each recommendation in combined_recommendations
                for recommendation in combined_recommendations:
                    id = recommendation["_id"]

                    # If article ID is not already in unique_recommendations or has lower score than existing recommendation,
                    # add the recommendation to unique_recommendations
                    if (
                        id not in unique_recommendations
                        or recommendation["score"] > unique_recommendations[id]["score"]
                    ):
                        unique_recommendations[id] = recommendation

                # Convert the dictionary of unique recommendations back into a list
                unique_recommendations_list = list(unique_recommendations.values())

                # Remove recommendations that are already in user's history
                unique_recommendations_list = [
                    rec
                    for rec in unique_recommendations_list
                    if rec["_id"] not in [h["_id"] for h in history_list]
                ]

                unique_recommendations_list = [
                    {"index": i + 1, **rec}
                    for i, rec in enumerate(unique_recommendations_list[:45])
                ]
                print("end recommendation")
                return unique_recommendations_list
                # Return combined recommendations as JSON response
                # return jsonify(
                #     {"email": email, "recommendations": unique_recommendations_list}
                # )         

@recommendation_bp.route("/save_recommendation", methods=["GET"])
@jwt_required()
def save_recommendation():
    email = get_jwt_identity()
    recommendations_news = calculate_recommendation(email)
    print(recommendations_news)
    print("calculate done")
    if recommendations_news != None:
        for recommendation in recommendations_news:
            news = News(recommendation["_id"], recommendation["original"], recommendation["title"], recommendation["content"], recommendation["image"], recommendation["date"], recommendation["media"], recommendation["kategori"])
            with driver.session() as session:
                news_exist = News.find_news(session, recommendation["_id"])
                if news_exist == None:
                    with driver.session() as session:
                        news.save_news(session)
                with driver.session() as session:
                    News.create_relation_similar(session, recommendation["id_history"], recommendation["_id"], recommendation["score"])
                    User.create_relation_recommend(session, email, recommendation["_id"], recommendation["index"])
        return jsonify({"message":"Recommendation saved successfully"}), 201 
    else:
        return jsonify({"message":"No recommendation"})

@recommendation_bp.route("/getmedia")
def get_media():
    with driver.session() as session:
        media_data = Media.get_all_media(session)

    media_list = [dict(m) for m in media_data]
    return media_list

@recommendation_bp.route("/recommendation", methods=["GET"])
@jwt_required()
def get_recommendation():
    data = []
    recommendation_list = {}
    email = get_jwt_identity()
    with driver.session() as session:
        news = User.get_recommendation(session, email)
    for record in news:
        with driver.session() as session:
            score = News.get_similarity(session, record["_id"])
            media = Media.get_relation_media(session, record["_id"])
            kategori = Category.get_relation_category(session, record["_id"])
            recommendation_list["_id"] = record["_id"]
            recommendation_list["score"] = score
            recommendation_list["original"] = record["original"]
            recommendation_list["title"] = record["title"]
            recommendation_list["content"] = record["content"]
            recommendation_list["image"] = record["image"]
            recommendation_list["date"] = record["date"]
            recommendation_list["media"] = media
            recommendation_list["kategori"] = kategori
            data.append(recommendation_list.copy())
    return jsonify(data)

@recommendation_bp.route("/index", methods=["GET"])
def test_get_index_max():
    with driver.session() as session:
        index = News.get_index_max(session, "naurathirahh@gmail.com")
    return jsonify(index)
