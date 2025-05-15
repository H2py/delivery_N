from flask import Flask
from datetime import datetime
from bson import ObjectId
import os
from werkzeug.security import generate_password_hash
from delivery_n.db import get_db

app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY='dev',
    MONGO_URI=os.getenv("MONGO_URI")
)

# id: 1000@naver.com부터 1019@naver.com
# password 1000부터 1019
def seed_users():
    with app.app_context():
        db = get_db()
        
        # 기존 테스트 계정 삭제 (선택적)
        db.users.delete_many({'email': {'$regex': '@naver.com$'}})
        db.otp_tokens.delete_many({'email': {'$regex': '@naver.com$'}})
        print("🗑️ 기존 테스트 계정 및 OTP 기록 삭제 완료.")

        # 20개 계정 생성
        for i in range(1000, 1020):
            username = f"user{i}"
            email = f"{i}@naver.com"
            password = str(i)  # 비밀번호: 1000 ~ 1019
            hashed_password = generate_password_hash(password)

            # OTP 인증 기록 삽입 (인증 완료 상태)
            db.otp_tokens.insert_one({
                'email': email,
                'verified': True,
                'created_at': datetime.now()
            })

            # 사용자 계정 삽입
            existing_user = db.users.find_one({'email': email, 'deleted_at': True})
            if existing_user:
                # 탈퇴한 계정 재활성화
                db.users.update_one(
                    {'_id': existing_user['_id']},
                    {
                        '$set': {
                            'username': username,
                            'password': hashed_password,
                            'email': email,
                            'deleted_at': None,
                            'is_active': True
                        },
                        '$unset': {'revoked_at': ''}
                    }
                )
                print(f"🔄 계정 재활성화: {email}")
            else:
                # 신규 계정 생성
                user_id = db.users.insert_one({
                    'username': username,
                    'email': email,
                    'password': hashed_password,
                    'deleted_at': None,
                    'is_active': True
                }).inserted_id
                print(f"✅ 신규 계정 생성: {email} (ID: {user_id})")

            db.otp_tokens.delete_one({'email': email})

        print("🎉 20개의 테스트 계정 생성 완료.")

if __name__ == "__main__":
    seed_users()