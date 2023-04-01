import os
from dotenv import load_dotenv

load_dotenv()

def get_db_username():
    return os.environ.get('DATABASE_USERNAME')

def get_db_password():
    return os.getenv('DATABASE_PASSWORD')

def get_db_url():
    return os.getenv('DATABASE_URL')

def get_mail_username():
    return os.getenv('MAIL_USERNAME')

def get_mail_password():
    return os.getenv('MAIL_PASSWORD')

def get_mail_server():
    return os.getenv('MAIL_SERVER')

def get_mail_port():
    return os.getenv('MAIL_PORT')


# DATABASE_USERNAME="neo4j"
# DATABASE_PASSWORD="neo4j123"
# DATABASE_URL="bolt://103.59.95.88:7687"
