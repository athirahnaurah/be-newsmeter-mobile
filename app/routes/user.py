import os
from cryptography.fernet import Fernet
from config import get_db_username, get_db_password, get_db_url, get_mail_username, get_mail_password, get_mail_server, get_mail_port
from flask import Blueprint, jsonify, request, render_template
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, jwt_required
from neo4j import GraphDatabase, basic_auth
from model.user import User
from flask_mail import Message
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

user_bp = Blueprint('user_bp', __name__)
bcrypt = Bcrypt()
key = Fernet.generate_key()
fernet = Fernet(key)

driver = GraphDatabase.driver(get_db_url(), auth=basic_auth(get_db_username(),get_db_password()))

@user_bp.route("/register", methods=["POST"])
def register():
    name = request.json["name"]
    email = request.json["email"]
    with driver.session() as session:
        user = User.find_by_email(session, email)
        if user:
            return jsonify({'error': 'Email has been used'})
    password = bcrypt.generate_password_hash(request.json["password"]).decode("utf-8")
    join = name + "," + email + "," + password
    access_token = fernet.encrypt(join.encode()).decode()
    send_activation_email(name, email, access_token)
    return jsonify({'message': 'Please check email to activate your account'})

@user_bp.route("/activate/<token>",methods=["GET"])
def activate(token):
    decToken = fernet.decrypt(token.encode()).decode()
    split = decToken.split(",")
    name = split[0]
    email = split[1]
    password = split[2]
    user = User(name, email, password)
    with driver.session() as session:
        user.create(session)
    # redirect ke aplikasi
    return jsonify({'message': 'Account activated.'})

def send_activation_email(name, email, token):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Activation Email"
    msg['From'] = get_mail_username()
    msg['To'] = email
    html_file = open('template/activation.html').read().replace("{{name}}",name).replace("{{ token }}", str(token))
    part2 = MIMEText(html_file, 'html')
    msg.attach(part2)

    s = smtplib.SMTP(get_mail_server(), get_mail_port())
    s.starttls()
    s.login(get_mail_username(), get_mail_password())
    s.sendmail(get_mail_username(), email, msg.as_string())
    s.quit()
    return 'Activation email sent'

@user_bp.route("/login", methods=["POST"])
def login():
    email = request.json["email"]
    password = request.json["password"]
    with driver.session() as session:
        user = User.find_by_email(session, email)
        if user and bcrypt.check_password_hash(user.password, password):
            access_token = create_access_token(identity=user.id)
            return jsonify({"access_token": access_token}), 200
        else:
            return "Invalid username or password", 401

@user_bp.route("/preference",methods=["POST"])
def choose_preference():
    email = request.json["email"]
    kategori = request.json["preference"]
    with driver.session() as session:
        user = User.create_preference(session, email, kategori)
    return jsonify({'message': 'User preferences saved successfully'}),200