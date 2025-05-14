from flask import Flask
from datetime import datetime, timedelta
from bson import ObjectId
import random
import os
from delivery_n.db import get_db

app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY='dev',
    MONGO_URI=os.getenv("MONGO_URI")
)

with app.app_context():
    db = get_db()
    
    dummy_posts = []
    author_id = ObjectId()

    for i in range(100):
        now = datetime.now()
        total_portion = random.randint(5, 10)
        my_portion = random.randint(1, 3)
        total_price = random.randint(10000, 50000)
        
        dummy_posts.append({
            'title': f'Dummy Post {i+1}',
            'store_name': f'Store {i+1}',
            'menus': [f'Menu {i+1}', f'Menu {i+2}'],
            'content': f'This is dummy content for post {i+1}',
            'author_id': author_id,
            'total_price': total_price,
            'my_portion': my_portion,
            'total_portion': total_portion,
            'deadline': now + timedelta(hours=random.randint(1, 24)),
            'status': True,
            'created_at': now,
            'updated_at': now,
            'url': f'https://kakao.com/dummy-chat/{i+1}',
            'participants': [
                {
                    'user_id': author_id,
                    'portion': my_portion,
                    'amount': (total_price // total_portion) * my_portion,
                    'status': 'confirmed',
                    'username': f'DummyUser{i+1}'
                }
            ]
        })

    result = db.posts.insert_many(dummy_posts)
    print(f"✅ {len(result.inserted_ids)}개의 게시글이 성공적으로 삽입되었습니다.")