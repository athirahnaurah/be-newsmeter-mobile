import os
from dotenv import load_dotenv
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, jwt_required, JWTManager
from routes.user import user_bp

app = Flask(__name__)
load_dotenv()
bcrypt = Bcrypt(app)
app.config["JWT_SECRET_KEY"] = os.getenv('JWT_SECRET_KEY')
jwt = JWTManager(app)
app.register_blueprint(user_bp)

if __name__ == "__main__":
    app.run()