from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from model.news import News
from model.category import Category
from model.user import User
from model.media import Media
from utils.connection import create_neo4j_connection

history_bp = Blueprint('history_bp', __name__)
driver = create_neo4j_connection()

@history_bp.route("/history", methods=["POST"])
@jwt_required()
def history():
    current_user = get_jwt_identity()
    data = request.get_json()
    news  = News(data["_id"], data["original"], data["title"], data["content"], data["image"], data["date"], data["media"], data["kategori"])
    with driver.session() as session:
        news_exist = News.find_news(session, data["_id"])
        if news_exist == None:
            with driver.session() as session:
                news.save_news(session)
                # News.create_relation_to_media(session, data["_id"], data["media"])
                # Category.create_relation_to_news(session, data["_id"], data["kategori"])
    check_read(current_user, data["media"])
    with driver.session() as session:
        User.save_history(session, current_user, data["_id"], data["timestamp"])
    return jsonify({"message":"History saved successfully"}), 201

def check_read(user, media):
    with driver.session() as session:
        visited = User.find_history_media(session, user)
        if media not in visited:
            with driver.session() as session:
                view = Media.find_total_view(session, media)
                view += 1
                Media.set_total_view(session, view, media)

@history_bp.route("/test", methods=["GET"])
def test():
    with driver.session() as session:
        media = User.find_history_media(session, "fathirahnaurah@gmail.com")
    return jsonify(media), 200