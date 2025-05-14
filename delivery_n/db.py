from pymongo import MongoClient
from datetime import datetime
from flask import current_app, g
from urllib.parse import quote_plus

def get_db():
    if 'db' not in g:
        # MongoDB Atlas 연결 설정
        uri = "mongodb+srv://anfakt0606:tkfkdgo12!@delivery-n.o2oro1i.mongodb.net/delivery-n?retryWrites=true&w=majority"
        
        try:
            client = MongoClient(uri)
            g.db = client['delivery-n']  # 하이픈을 사용한 데이터베이스 이름으로 접근
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
