from pymongo import MongoClient
import datetime
from flask import current_app, g
from urllib.parse import quote_plus
import os

def get_db():
    if 'db' not in g:
        # MongoDB Atlas 연결 설정
        uri = os.getenv("MONGO_URI")
        
        try:
            client = MongoClient(uri)
            g.db = client.get_database()
        except Exception as e:
            print(f"MongoDB 연결 실패: {e}")
            raise
    
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.client.close()
        
def init_db(app):
    app.teardown_appcontext(close_db)
