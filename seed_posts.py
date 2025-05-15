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

# 메뉴 및 가게명 매핑
MENU_STORE_MAPPING = {
    '치킨': {'store': '황금올리브', 'sub_menus': ['후라이드', '양념', '간장']},
    '피자': {'store': '화덕에빠진피자', 'sub_menus': ['페퍼로니', '하와이안', '콤비네이션']},
    '짜장면': {'store': '용용각', 'sub_menus': []},
    '짬뽕': {'store': '불꽃해물짬뽕', 'sub_menus': []},
    '탕수육': {'store': '홍보각', 'sub_menus': []},
    '볶음밥': {'store': '불맛쉐프', 'sub_menus': []},
    '김밥': {'store': '어머니손김밥', 'sub_menus': []},
    '떡볶이': {'store': '매운공주', 'sub_menus': []},
    '족발': {'store': '왕발통족발', 'sub_menus': []},
    '보쌈': {'store': '도야지상회', 'sub_menus': []},
    '삼겹살': {'store': '숯불달인', 'sub_menus': []},
    '국수': {'store': '면사랑', 'sub_menus': ['냉면', '비빔국수']},
    '햄버거': {'store': '버거펍', 'sub_menus': ['치즈버거', '불고기버거']},
    '도시락': {'store': '맘스런치박스', 'sub_menus': ['김치볶음밥', '제육볶음']},
    '순대국밥': {'store': '할매순대국', 'sub_menus': []},
    '찜닭': {'store': '안동본가', 'sub_menus': []},
    '마라탕': {'store': '화룡점정', 'sub_menus': []},
    '돈까스': {'store': '왕돈카츠', 'sub_menus': []},
    '닭갈비': {'store': '춘천맛집', 'sub_menus': []},
    '김치찌개': {'store': '오모가매운지', 'sub_menus': ['김치찌개', '된장찌개']}
}

def seed_posts():
    with app.app_context():
        db = get_db()
        
        # 테스트 계정 목록 조회
        test_users = list(db.users.find({
            'email': {'$regex': '@naver.com$'},
            'is_active': True,
            'deleted_at': None
        }))
        if not test_users:
            print("⚠️ 테스트 계정이 없습니다. 먼저 seed_users.py를 실행하세요.")
            return

        # 기존 데이터 삭제
        db.posts.delete_many({})
        db.participants.delete_many({})
        print("🗑️ 기존 더미 포스트 및 참여자 데이터 삭제 완료.")

        dummy_posts = []
        dummy_participants = []
        menu_keys = list(MENU_STORE_MAPPING.keys())

        for i in range(100):
            now = datetime.now()
            total_portion = random.randint(5, 10)
            my_portion = random.randint(1, 3)
            total_price = random.randint(10000, 50000)
            
            # 랜덤 사용자 선택
            user = random.choice(test_users)
            user_id = user['_id']
            username = user['username']
            
            # 메뉴 1~2개 랜덤 선택
            num_menus = random.randint(1, 2)
            selected_menus = random.sample(menu_keys, num_menus)
            menus = []
            for menu in selected_menus:
                sub_menus = MENU_STORE_MAPPING[menu]['sub_menus']
                if sub_menus:
                    sub_menu = random.choice(sub_menus)
                    menus.append(f"{menu} ({sub_menu})")
                else:
                    menus.append(menu)
            
            # 가게명: 첫 번째 메뉴에 대응
            store_name = MENU_STORE_MAPPING[selected_menus[0]]['store']
            
            # 제목 생성
            if any(menu.startswith(('치킨', '피자')) for menu in selected_menus):
                title = "피자, 치킨 같이 먹어요~"
            else:
                title = f"{', '.join(selected_menus)} 같이 먹어요~"
            
            # 더미 포스트 데이터
            post = {
                'title': title,
                'store_name': store_name,
                'menus': menus,
                'content': f"이건 {', '.join(menus)}를 위한 더미 포스트입니다!",
                'author_id': ObjectId(user_id),
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
                        'user_id': ObjectId(user_id),
                        'portion': my_portion,
                        'amount': (total_price / total_portion) * my_portion,
                        'status': '확정',
                        'username': username
                    }
                ]
            }
            dummy_posts.append(post)

        # 포스트 삽입
        result = db.posts.insert_many(dummy_posts)
        print(f"✅ {len(result.inserted_ids)}개의 게시글이 성공적으로 삽입되었습니다.")

        # 참여자 데이터 생성 및 삽입
        for post, inserted_id in zip(dummy_posts, result.inserted_ids):
            participant_data = {
                'post_id': inserted_id,
                'user_id': post['author_id'],
                'portion': post['my_portion'],
                'amount': (post['total_price'] / post['total_portion']) * post['my_portion'],
                'status': '확정',
                'created_at': now,
                'updated_at': now
            }
            dummy_participants.append(participant_data)

        # 참여자 삽입
        if dummy_participants:
            db.participants.insert_many(dummy_participants)
            print(f"✅ {len(dummy_participants)}개의 참여자 데이터가 성공적으로 삽입되었습니다.")

if __name__ == "__main__":
    seed_posts()