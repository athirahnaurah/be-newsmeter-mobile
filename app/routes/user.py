import os
from cryptography.fernet import Fernet
from config import get_mail_username, get_mail_password, get_mail_server, get_mail_port
from utils.connection import create_neo4j_connection
from flask import Blueprint, jsonify, request, redirect
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    unset_jwt_cookies,
)
from model.user import User
from model.media import Media
from flask_mail import Message
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json


user_bp = Blueprint("user_bp", __name__)
bcrypt = Bcrypt()
key = Fernet.generate_key()
fernet = Fernet(key)

driver = create_neo4j_connection()


@user_bp.route("/register", methods=["POST"])
def register():
    name = request.json["name"]
    email = request.json["email"]
    with driver.session() as session:
        user = User.find_by_email(session, email)
        if user:
            return jsonify({"error": "Email has been used"}), 404
    password = bcrypt.generate_password_hash(request.json["password"]).decode("utf-8")
    join = name + "," + email + "," + password
    access_token = fernet.encrypt(join.encode()).decode()
    send_activation_email(name, email, access_token)
    return jsonify({"message": "Please check email to activate your account"})


@user_bp.route("/activate/<token>", methods=["GET"])
def activate(token):
    decToken = fernet.decrypt(token.encode()).decode()
    split = decToken.split(",")
    name = split[0]
    email = split[1]
    password = split[2]
    user = User(name, email, password)
    with driver.session() as session:
        user.create(session)
    url = "newsmeter://minatkategori/email"
    return redirect(url, code=302)


def send_activation_email(name, email, token):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Activation Email"
    msg["From"] = get_mail_username()
    msg["To"] = email
    html_file = (
        open("template/activation.html")
        .read()
        .replace("{{name}}", name)
        .replace("{{ token }}", str(token))
    )
    part2 = MIMEText(html_file, "html")
    msg.attach(part2)

    s = smtplib.SMTP(get_mail_server(), get_mail_port(), timeout=200)
    s.starttls()
    s.login(get_mail_username(), get_mail_password())
    s.sendmail(get_mail_username(), email, msg.as_string())
    s.quit()
    return "Activation email sent"


@user_bp.route("/login", methods=["POST"])
def login():
    email = request.json["email"]
    password = request.json["password"]
    with driver.session() as session:
        user = User.find_by_email(session, email)
        if user and bcrypt.check_password_hash(user.password, password):
            access_token = create_access_token(identity=user.email)
            return jsonify({"access_token": access_token}), 200
        else:
            return "Invalid username or password", 401


@user_bp.route("/logout", methods=["GET"])
@jwt_required()
def logout():
    response = jsonify({"message": "Logout berhasil"})
    unset_jwt_cookies(response)
    return response


@user_bp.route("/user", methods=["GET"])
@jwt_required()
def get_user_login():
    current_user = get_jwt_identity()
    with driver.session() as session:
        user = User.find_by_email(session, current_user)
    if user:
        return jsonify({"name": user.name, "email": user.email}), 200
    else:
        return jsonify({"message": "User not found"}), 404


@user_bp.route("/preference", methods=["POST"])
def choose_preference():
    email = request.json["email"]
    kategori = request.json["preference"]
    with driver.session() as session:
        user = User.find_by_email(session, email)
        if user:
            result = User.create_preference(session, email, kategori)
            if result:
                return jsonify({"message": "User preferences saved successfully"}), 201
            else:
                return jsonify({"message": "User preferences failed to save"}), 400
        else:
            return jsonify({"message": "User not found"}), 404


@user_bp.route("/preference", methods=["GET"])
@jwt_required()
def get_preference():
    current_user = get_jwt_identity()
    with driver.session() as session:
        preference = User.find_preference(session, current_user)
    if preference:
        return jsonify(preference), 200
    else:
        return jsonify({"message": "User preferences not found"}), 404
