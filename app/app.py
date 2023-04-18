import os
from dotenv import load_dotenv
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, jwt_required, JWTManager
from routes.user import user_bp
from routes.history import history_bp
from datetime import timedelta, datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
load_dotenv()
bcrypt = Bcrypt(app)
app.config["JWT_SECRET_KEY"] = os.getenv('JWT_SECRET_KEY')
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=90)
jwt = JWTManager(app)
app.register_blueprint(user_bp)
app.register_blueprint(history_bp)


if __name__ == "__main__":
    app.run()