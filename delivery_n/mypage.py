from flask import Blueprint, json, make_response, render_template, request, redirect, url_for, session, flash, g, jsonify
from datetime import datetime
from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request
from werkzeug.exceptions import abort
from werkzeug.security import generate_password_hash, check_password_hash
from .auth import login_required
from .db import get_db
from werkzeug.security import generate_password_hash
from bson.objectid import ObjectId
from .utils import make_json_response

bp = Blueprint('mypage', __name__, url_prefix='/mypage')

@bp.route('/my_write', methods=['GET'])
@login_required
def my_write():
    db = get_db()

    page = int(request.args.get('page', 1))
    per_page = 10
    skip = (page - 1) * per_page
    
    total_posts = db.posts.count_documents({})
    total_pages = (total_posts + per_page - 1) // per_page 
    
    block_size = 5
    block_index = (page - 1) // block_size
    start_page = block_index * block_size + 1
    end_page = min(start_page + block_size - 1, total_pages)

    posts = db.posts.aggregate([
        {
            "$match": {"author_id": ObjectId(g.user['_id'])}
        },
        {
            "$sort": { "deadline": 1 }
        },
        {
            "$lookup": {
                "from": "users",
                "localField": "author_id",
                "foreignField": "_id",
                "as": "author"
            }
        },
        {
            "$lookup": {
                "from": "participants",
                "localField": "_id",
                "foreignField": "post_id",
                "as": "participants"
            }
        },
        {
            "$set": {
                "author": {
                    "$cond": {
                        "if": { "$gt": [{ "$size": "$author" }, 0] },
                        "then": { "$arrayElemAt": ["$author", 0] },
                        "else": { "username": "알 수 없음" }
                    }
                },
                "current_participants": { "$size": "$participants" }
            }
        },
        {
            "$project": {
                "id": "$_id",
                "title": 1,
                "content": 1,
                "author_id": 1,
                "username": "$author.username",
                "store_name": 1,
                "menus": 1,
                "total_price": 1,
                "my_portion": 1,
                "total_portion": 1,
                "current_participants": 1,
                "deadline": 1,
                "status": 1,
                "created_at": 1,
                "updated_at": 1
            }
        },
        {
            "$sort": {"created_at": -1}
        }
    ])
    return render_template('mypage/myWriteList.html', posts=list(posts), page=page, total_pages=total_pages, start_page=start_page, end_page=end_page)


@bp.route('/my_join', methods=['GET'])
@login_required
def my_join():
    db = get_db()

    page = int(request.args.get('page', 1))
    per_page = 10
    skip = (page - 1) * per_page
    
    # participants 컬렉션에서 사용자가 참여한 게시글 조회
    pipeline = [
        {
            "$match": {
                "user_id": ObjectId(g.user['_id'])
            }
        },
        {
            "$lookup": {
                "from": "posts",
                "localField": "post_id",
                "foreignField": "_id",
                "as": "post"
            }
        },
        {
            "$unwind": "$post"
        },
        {
            "$lookup": {
                "from": "users",
                "localField": "post.author_id",
                "foreignField": "_id",
                "as": "author"
            }
        },
        {
            "$lookup": {
                "from": "participants",
                "localField": "post._id",
                "foreignField": "post_id",
                "as": "all_participants"
            }
        },
        {
            "$set": {
                "author": {
                    "$cond": {
                        "if": { "$gt": [{ "$size": "$author" }, 0] },
                        "then": { "$arrayElemAt": ["$author", 0] },
                        "else": { "username": "알 수 없음" }
                    }
                },
                "current_participants": { "$size": "$all_participants" }
            }
        },
        {
            "$project": {
                "id": "$post._id",
                "title": "$post.title",
                "content": "$post.content",
                "author_id": "$post.author_id",
                "username": "$author.username",
                "store_name": "$post.store_name",
                "menus": "$post.menus",
                "total_price": "$post.total_price",
                "my_portion": "$post.my_portion",
                "total_portion": "$post.total_portion",
                "deadline": "$post.deadline",
                "status": "$post.status",
                "created_at": "$post.created_at",
                "updated_at": "$post.updated_at",
                "participant_status": "$status",
                "participant_portion": "$portion",
                "participant_amount": "$amount",
                "current_participants": 1
            }
        },
        {
            "$sort": { "deadline": 1 }
        },
        {
            "$skip": skip
        },
        {
            "$limit": per_page
        }
    ]
    
    # 전체 문서 수 계산을 위한 카운트 파이프라인
    count_pipeline = [
        {
            "$match": {
                "user_id": ObjectId(g.user['_id'])
            }
        }
    ]
    
    total_posts = len(list(db.participants.aggregate(count_pipeline)))
    total_pages = (total_posts + per_page - 1) // per_page
    
    block_size = 5
    block_index = (page - 1) // block_size
    start_page = block_index * block_size + 1
    end_page = min(start_page + block_size - 1, total_pages)
    
    posts = list(db.participants.aggregate(pipeline))
    
    return render_template('mypage/myJoinList.html', 
                         posts=posts, 
                         page=page, 
                         total_pages=total_pages, 
                         start_page=start_page, 
                         end_page=end_page)


@bp.route('/modify_name', methods=['GET', 'POST'])
# @login_required
def modify_name():
    db = get_db()
    if request.method == 'POST':
        data = request.get_json()
        new_username = data.get('username')
        error = None

        if not new_username:
            error = '닉네임을 입력해주세요.'
        elif len(new_username) > 20:
            error = '닉네임은 20자 이내여야 합니다.'

        if error:
             return make_json_response(False, error)

        db.users.update_one(
            {"_id": ObjectId(g.user['_id'])},
            {"$set": {"username": new_username}}
        )
        g.user['username'] = new_username  
        return make_json_response(True, "닉네임이 성공적으로 변경되었습니다.")


    return render_template('mypage/mypage.html')


@bp.route('/modify_password', methods=['GET', 'POST'])
# @login_required
def modify_password():
    db = get_db()

    if request.method == 'POST':
        data = request.get_json()   
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        user = db.users.find_one({'_id': ObjectId(g.user['_id'])})

        if not current_password or not check_password_hash(user['password'], current_password):
            return make_json_response(False, "현재 비밀번호가 일치하지 않습니다.")
        if not new_password or not confirm_password:
            return make_json_response(False, "새 비밀번호와 확인칸 모두 입력해주세요.")
        if new_password != confirm_password:
            return make_json_response(False, "새 비밀번호가 일치하지 않습니다.")
        if len(new_password) < 5:
            return make_json_response(False, "새 비밀번호는 5자 이상이어야 합니다.")
        if check_password_hash(user['password'], new_password):
            return make_json_response(False, "기존 비밀번호와 다른 비밀번호를 입력해주세요.")
     
        db.users.update_one(
            {"_id": ObjectId(g.user['_id'])},
            {"$set": {"password": generate_password_hash(new_password)}}
        )
        return make_json_response(True, "비밀번호가 성공적으로 변경되었습니다.")

    return render_template('mypage/modify_password.html')


@bp.route('/my_posts', methods=['GET'])
# @login_required
def my_posts():
    db = get_db()
    posts_cursor = db.posts.find(
        {"author_id": ObjectId(g.user['_id'])}
    ).sort("created_at", -1)

    posts = []
    for post in posts_cursor:
        posts.append({
            "_id": str(post["_id"]),
            "title": post["title"],
            "content": post["content"],
            "author_id": str(post["author_id"]),
            "created_at": post.get("created_at").isoformat() if post.get("created_at") else None
        })

    return make_json_response(True, "내 게시글 목록입니다.", posts)


@bp.route('/delete_account', methods=['POST'])
def delete_account():
    db = get_db()
    
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()

        if user_id:
            data = request.get_json()
            password = data.get('password')

            # 현재 사용자 정보 가져오기
            user = db.users.find_one({'_id': ObjectId(user_id)})
            
            if not user:
                return make_json_response(False, "사용자를 찾을 수 없습니다.")

            # 비밀번호 검증
            if not check_password_hash(user['password'], password):
                return make_json_response(False, "비밀번호가 일치하지 않습니다.")

            # 회원 탈퇴 처리
            db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {
                    'deleted_at': datetime.now(),
                    'is_active': False    
                }}
            )
            
            # 토큰 무효화
            db.tokens.update_one(
                {
                    'user_id': ObjectId(user_id),
                    'is_revoked': False
                },
                {'$set': {
                    'is_revoked': True,
                    'revoked_at': datetime.now()
                }}
            )

            # 회원 탈퇴 완료 후 응답
            response = make_response()
            response.delete_cookie('access_token_cookie', path='/')
            response.delete_cookie('refresh_token_cookie', path='/')
            response.set_data(json.dumps({
                'success': True,
                'message': "회원 탈퇴가 완료되었습니다.",
                'data': {'redirect_url': url_for('auth.login')}
            }))
            response.headers['Content-Type'] = 'application/json'
            return response, 200

    except Exception as e:
        print(f"계정 삭제 중 오류: {str(e)}")
        return make_json_response(False, f"오류가 발생했습니다: {str(e)}")

    return make_json_response(False, "잘못된 접근입니다.")
