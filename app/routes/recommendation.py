from flask import Blueprint, jsonify, request
import pandas as pd
import re, requests
from nltk.corpus import stopwords
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
from bs4 import BeautifulSoup
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.linalg import svd
from sklearn.metrics.pairwise import cosine_similarity

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


def preprocessing_content():
    response = requests.get(
        "http://103.59.95.88/api/get/news/10?fields=_id,original,title,content,image,date"
    )
    data = response.json()
    for i, item in enumerate(data):
        item["id"] = i + 1
    df = pd.DataFrame.from_dict(data)
    df["content"] = df["content"].apply(preprocess_text)
    return df


def calculate_recommendation(df):
    # Create the TF-IDF matrix
    tf = TfidfVectorizer()
    # Transform TFIDF to Content
    tfidf_matrix = tf.fit_transform(df["content"])
    # SVD & Konversi Matrix Sparse -> Dense
    V, S, U = svd(tfidf_matrix.todense())
    # Perkalian Matriks V dan S
    VS = np.dot(V, np.diag(S))
    # Cosine similarity matriks VS
    cosine_similarities = cosine_similarity(VS)
    results = {}
    for idx, row in df.iterrows():
        similar_indices = cosine_similarities[idx].argsort()[:-100:-1]
        similar_items = [
            (cosine_similarities[idx][i], df["id"][i]) for i in similar_indices
        ]
        # First item is the item itself, so remove it.
        # Each dictionary entry is like: [(1,2), (3,4)], with each tuple being (score, item_id)
        results[row["id"]] = similar_items[1:]

    return results


df = preprocessing_content()
results = calculate_recommendation(df)


def item(id):
    _id = df.loc[df["id"] == id, "_id"].iloc[0]
    title = df.loc[df["id"] == id, "title"].iloc[0]
    return _id, title


@recommendation_bp.route("/recommendation/<int:item_id>")
def get_recommendation(item_id):
    result = {}
    result["recommendation"] = []
    recs = results.get(item_id, [])[:3]
    for rec in recs:
        recommendation = {}
        recommendation["score"] = str(rec[0])
        _id, title = item(rec[1])
        recommendation["_id"] = _id
        recommendation["title"] = title
        result["recommendation"].append(recommendation)
    return jsonify(result)
