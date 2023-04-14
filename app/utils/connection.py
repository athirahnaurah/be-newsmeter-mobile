from neo4j import GraphDatabase, basic_auth
from config import get_db_username, get_db_password, get_db_url

def create_neo4j_connection():
    return GraphDatabase.driver(get_db_url(), auth=basic_auth(get_db_username(),get_db_password()))