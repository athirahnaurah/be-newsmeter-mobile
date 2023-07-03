import os
from dotenv import load_dotenv
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, jwt_required, JWTManager
from routes.user import user_bp
from routes.history import history_bp
from routes.recommendation import (
    recommendation_bp,
    # call_save_recommendation,
    # schedule_save_recommendation,
)
from datetime import timedelta, datetime
from flask_cors import CORS

# import schedule
# import time
# import threading
# import requests
# import pytz


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
load_dotenv()
bcrypt = Bcrypt(app)
app.secret_key = os.getenv("JWT_SECRET_KEY")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=90)
jwt = JWTManager(app)
app.register_blueprint(user_bp)
app.register_blueprint(history_bp)
app.register_blueprint(recommendation_bp)


if __name__ == "__main__":
    # schedule.every().day.at("00:00").do(call_save_recommendation)
    # schedule_thread = threading.Thread(target=schedule_save_recommendation)
    # schedule_thread.start()
    app.run(debug=True)
