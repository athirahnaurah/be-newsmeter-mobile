import os
import re, requests
import pandas as pd
import numpy as np
import time, datetime
from datetime import timedelta
from flask import Blueprint, jsonify, request, session
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
from utils.format_date import convert_to_string
from model.user import User
from model.media import Media
from model.news import News
from model.category import Category
from api.api import API
import schedule
import time
import dotenv
import concurrent.futures
import math
from functools import partial

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


def get_prepocessing_history(email):
    time_now = datetime.datetime.now().timestamp()
    time_12_hours_ago = (
        # edit jam history
        datetime.datetime.now()
        - datetime.timedelta(hours=12)
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
    data = data[["_id", "original", "title", "content", "image", "date", "id_has_read"]]

    # Remove duplicate entries based on the "_id" column
    data = data.drop_duplicates(subset="_id", keep="first")

    data["preprocessed_content"] = data["content"].apply(preprocess_text)
    return data.to_dict("records")


def get_preprocessing_new_news(email):
    response = requests.get(API.NEWS_URL)
    data = response.json()
    if not data:
        return None
    df = pd.DataFrame.from_dict(data)
    df = df[
        ["_id", "original", "title", "content", "image", "date", "kategori", "media"]
    ]
    df["preprocessed_content"] = df["content"].apply(preprocess_text)

    history_list = remove_existing_news_from_history(df, email)

    return history_list.to_dict("records")


def remove_existing_news_from_history(df, email):
    history_list = get_prepocessing_history(email)

    if history_list is not None:
        history_df = pd.DataFrame.from_dict(history_list)
        existing_ids = history_df["_id"].tolist()
        filtered_df = df[~df["_id"].isin(existing_ids)]
    else:
        filtered_df = df

    return filtered_df


def calculate_recommendation(email):
    print("start preprocessing history")
    start = time.time()
    history_list = get_prepocessing_history(email)
    end = time.time()
    delta = timedelta(seconds=end - start)
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    seconds = delta.seconds % 60
    print("end preprocessing history")
    print(
        "duration preprocessing: {} hours, {} minutes, {} seconds".format(
            hours, minutes, seconds
        )
    )
    if not history_list:
        print("No history")
        return None
    else:
        print("start preprocessing new news")
        start = time.time()
        df = get_preprocessing_new_news(email)
        end = time.time()
        delta = timedelta(seconds=end - start)
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        seconds = delta.seconds % 60
        print("end preprocessing new news")
        print(
            "duration preprocessing: {} hours, {} minutes, {} seconds".format(
                hours, minutes, seconds
            )
        )
        if not df:
            return {"message": "No news found"}
        else:
            print("start tf-idf svd cosine-similarity")
            start = time.time()
            recommendation_data = []
            for i in range(0, len(df), len(df)):
                temp_df = df[i : i + len(df)]
                print("LSA 1 history with", len(df), "news")
                for j in range(len(history_list)):
                    concat_df = pd.concat(
                        [
                            pd.DataFrame.from_dict(history_list[j], orient="index").T,
                            pd.DataFrame.from_dict(temp_df),
                        ],
                        ignore_index=True,
                    )
                    concat_df.insert(0, "id", range(1, 1 + len(concat_df)))

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
                        recommendation["id_has_read"] = concat_df.loc[0, "id_has_read"]
                        recommendation["_id"] = str(concat_df.loc[index, "_id"])
                        recommendation["original"] = concat_df.loc[index, "original"]
                        recommendation["title"] = concat_df.loc[index, "title"]
                        recommendation["image"] = concat_df.loc[index, "image"]
                        recommendation["date"] = concat_df.loc[index, "date"]
                        recommendation["kategori"] = concat_df.loc[index, "kategori"]
                        recommendation["media"] = concat_df.loc[index, "media"]
                        recommendation["content"] = concat_df.loc[index, "content"]
                        result["recommendation"].append(recommendation)
                    recommendation_data.append(result)
            print("end tf-idf svd cosine similarity")
            end = time.time()
            print("duration LSA: ", end - start, "seconds")
    return recommendation_data


def sort_recommendation(email):
    data = calculate_recommendation(email)
    if data != None:
        combined_recommendations = []
        for result in data:
            combined_recommendations.extend(result["recommendation"])
        combined_recommendations = sort(combined_recommendations)

        relation = check_relation_recommend(email)
        if relation is None:
            combined_recommendations = [
                {"index": i + 1, **rec}
                for i, rec in enumerate(combined_recommendations[:45])
            ]
        else:
            max_index = get_index_max(email)
            combined_recommendations = [
                {"index": i + max_index + 1, **rec}
                for i, rec in enumerate(combined_recommendations[:45])
            ]

        print("End recommendation for:", email)
        # print("Final Recommendations:", combined_recommendations)
        return combined_recommendations
    else:
        return None


def sort(recommendations):
    df = pd.DataFrame(recommendations)
    df["view"] = 0
    media = get_all_media()
    for m in media:
        medianame = m["name"]
        df.loc[df["media"] == medianame, "view"] = m["view"]
    df = df.sort_values(["score", "date", "view"], ascending=[False, False, False])

    unique_recommendations = {}
    for idx, recommendation in df.iterrows():
        id = recommendation["_id"]
        if (
            id not in unique_recommendations
            or recommendation["score"] > unique_recommendations[id]["score"]
        ):
            unique_recommendations[id] = recommendation.to_dict()

    unique_recommendations_list = list(unique_recommendations.values())
    df = pd.DataFrame(unique_recommendations_list)
    df = df.drop_duplicates(subset=["_id", "score"], keep="first")
    if "id_history" in df.columns:
        return df[
            [
                "_id",
                "id_history",
                "score",
                "original",
                "title",
                "content",
                "image",
                "date",
                "media",
                "kategori",
                "id_has_read",
            ]
        ].to_dict(orient="records")
    else:
        # return df.to_dict(orient="records")
        return df[
            [
                "_id",
                "score",
                "original",
                "title",
                "content",
                "image",
                "date",
                "media",
                "kategori",
            ]
        ].to_dict(orient="records")


def get_all_media():
    with driver.session() as session:
        media_data = Media.get_all_media(session)
    return media_data


def get_index_max(email):
    with driver.session() as session:
        index = News.get_index_max(session, email)
    return index


def check_relation_recommend(email):
    with driver.session() as session:
        recommend = News.check_relation_recommend(session, email)
    return recommend


@recommendation_bp.route("/save_recommendation", methods=["GET"])
def run_recommendation():
    print("save_recommendation mulai")
    with driver.session() as session:
        now = convert_to_string(datetime.datetime.now().timestamp())
        time_12_hours_ago = convert_to_string(
            (datetime.datetime.now() - datetime.timedelta(hours=12)).timestamp()
        )
        users = User.find_reader(session, time_12_hours_ago, now)
    if users == None:
        return jsonify({"message": "There are no users reading the news"})
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            result = executor.map(partial(save_recommendation), users)
        executor.shutdown()
        concurrent.futures.as_completed(result)
        return (
            jsonify(
                {"message: ": "All tasks completed, recommendation saved successfully"}
            ),
            201,
        )


def save_recommendation(email):
    print("Start recommendation for: ", email)
    start = time.time()
    recommendations_news = sort_recommendation(email)
    end = time.time()
    delta = timedelta(seconds=end - start)
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    seconds = delta.seconds % 60
    print(
        "duration recommendation: {} hours, {} minutes, {} seconds".format(
            hours, minutes, seconds
        )
    )
    if recommendations_news != None:
        print("Result Recommendation for ", email, ":")
        i = 0
        for logRecom in recommendations_news:
            i = i + 1
            print(
                i,
                ")",
                "_id:",
                logRecom["_id"],
                " title:",
                logRecom["title"],
                " date:",
                logRecom["date"],
                " score:",
                logRecom["score"],
            )
        for recommendation in recommendations_news:
            news = News(
                recommendation["_id"],
                recommendation["original"],
                recommendation["title"],
                recommendation["content"],
                recommendation["image"],
                recommendation["date"],
                recommendation["media"],
                recommendation["kategori"],
            )
            with driver.session() as session:
                news_exist = News.find_news(session, recommendation["_id"])
            if news_exist == None:
                with driver.session() as session:
                    news.save_news(session)
            with driver.session() as session:
                News.create_relation_similar(
                    session,
                    recommendation["id_history"],
                    recommendation["_id"],
                    recommendation["score"],
                    recommendation["id_has_read"],
                )
                User.create_relation_recommend(
                    session, email, recommendation["_id"], recommendation["index"], recommendation["id_has_read"]
                )
        return "Recommendation saved successfully"
    else:
        return None


@recommendation_bp.route("/get_recommendation", methods=["GET"])
@jwt_required()
def get_recommendation():
    data = []
    recommendation_list = {}
    email = get_jwt_identity()
    with driver.session() as session:
        news = User.get_recommendation(session, email)
    if news:
        for record in news:
            with driver.session() as session:
                media = Media.get_relation_media(session, record["_id"])
                kategori = Category.get_relation_category(session, record["_id"])
                recommendation_list["_id"] = record["_id"]
                recommendation_list["score"] = record["score"]
                recommendation_list["original"] = record["original"]
                recommendation_list["title"] = record["title"]
                recommendation_list["content"] = record["content"]
                recommendation_list["image"] = record["image"]
                recommendation_list["date"] = record["date"]
                recommendation_list["media"] = media
                recommendation_list["kategori"] = kategori
                data.append(recommendation_list.copy())
        print(len(data))
        if len(data) < 45:
            i = 0
            for logData in data:
                i = i + 1
                print(
                    i,
                    ")",
                    "_id:",
                    logData["_id"],
                    " title:",
                    logData["title"],
                    " date:",
                    logData["date"],
                    " score:",
                    logData["score"],
                )
            return jsonify(data)
        else:
            sorted_data = sort(data)
            i = 0
            for logSortedData in sorted_data:
                i = i + 1
                print(
                    i,
                    ")",
                    "_id:",
                    logSortedData["_id"],
                    " title:",
                    logSortedData["title"],
                    " date:",
                    logSortedData["date"],
                    " score:",
                    logSortedData["score"],
                )
            return jsonify(sorted_data)
    else:
        return jsonify({"message:": "The user has no recommendations yet"})


def call_save_recommendation():
    response = requests.get("http://127.0.0.1:5000/save_recommendation")
    if response.status_code == 201:
        data = response.json()
        print(data)
    else:
        print("Request API failed with status code:", response.status_code)


def schedule_save_recommendation():
    while True:
        schedule.run_pending()
        time.sleep(1)
