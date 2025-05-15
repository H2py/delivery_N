from flask import Flask
from datetime import datetime, timedelta
from bson import ObjectId
import random
import os
import sys
from delivery_n.db import get_db

app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY='dev',
    MONGO_URI=os.getenv("MONGO_URI")
)
# python3 seed_posts.py 6824c6ab6c8032350abd5c4c 사용 방법
def seed_posts(user_id=None):
    with app.app_context():
        db = get_db()
        
        # 사용자 정보 조회
        if user_id:
            try:
                user = db.users.find_one({'_id': ObjectId(user_id)})
                if not user:
                    print(f"⚠️ 사용자 ID {user_id}를 찾을 수 없습니다. 임시 사용자 생성.")
                    user_id = str(ObjectId())
                    username = f"DummyUser_{user_id[:8]}"
                else:
                    username = user.get('username', f"User_{user_id[:8]}")
            except Exception as e:
                print(f"⚠️ 사용자 ID 처리 오류: {e}")
                user_id = str(ObjectId())
                username = f"DummyUser_{user_id[:8]}"
        else:
            print("⚠️ 사용자 ID가 제공되지 않았습니다. 임시 사용자 생성.")
            user_id = str(ObjectId())
            username = f"DummyUser_{user_id[:8]}"

        dummy_posts = []

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
                'author_id': ObjectId(user_id),  # 제공된 사용자 ID
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
                        'user_id': ObjectId(user_id),  # 동일한 사용자 ID
                        'portion': my_portion,
                        'amount': (total_price // total_portion) * my_portion,
                        'status': 'confirmed',
                        'username': username  # 사용자 이름
                    }
                ]
            })

        result = db.posts.insert_many(dummy_posts)
        print(f"✅ {len(result.inserted_ids)}개의 게시글이 성공적으로 삽입되었습니다.")

if __name__ == "__main__":
    # 명령줄 인수로 사용자 ID 받기
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    seed_posts(user_id)