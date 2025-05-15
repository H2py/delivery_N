from datetime import datetime
from flask import Blueprint, flash, g, redirect, render_template, request, url_for, jsonify
from werkzeug.exceptions import abort

from delivery_n.utils import make_json_response
from .auth import login_required
from .db import get_db
from bson.objectid import ObjectId
from flask import current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from .utils import make_json_response


bp = Blueprint('blog', __name__)

# def get_korea_time():
#     return datetime.now(pytz.timezone('Asia/Seoul'))

@bp.route('/')
def index():
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
    
    posts_cursor = db.posts.aggregate([
        {
            "$match": {
                "deadline": { "$gt": datetime.now(timezone.utc) }  # 현재 시간보다 마감시간이 더 큰 것만 필터링
            }
        },
        { "$sort": { "deadline": 1 } },  # 마감시간 오름차순 정렬
        { "$skip": skip },
        { "$limit": per_page },
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
        }#
    ])

    posts_list = list(posts_cursor)

    return render_template('main.html', posts=posts_list, page=page, total_pages=total_pages, start_page=start_page, end_page=end_page)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        try:
            data = request.get_json() or {}

            # JWT에서 user_id 가져오기
            author_id = get_jwt_identity()

            # 필수 필드 검증
            required_fields = ['title', 'store_name', 'menus', 'content', 'total_price', 'my_portion', 'total_portion']
            for field in required_fields:
                if not data.get(field):
                    return make_json_response(False, f'{field} is required.') , 400

            # 현재 시간
            current_time = get_korea_time()
            
            post_data = {
                'title': data['title'],
                'store_name': data['store_name'],
                'menus': data['menus'],
                'content': data['content'],
                'author_id': ObjectId(author_id),
                'total_price': data['total_price'],
                'my_portion': data['my_portion'],
                'total_portion': data['total_portion'],
                'deadline': datetime.strptime(data['deadline'], "%Y-%m-%dT%H:%M"),
                'status': True,
                'created_at': current_time,
                'updated_at': current_time,
                'url': data['url']
            }
            # URL 선택적 추가
            url = data.get('url', '').strip()
            if url:
                post_data['url'] = url
            
            db = get_db()
            result = db.posts.insert_one(post_data)
            if result.inserted_id:
                # 게시글 작성자를 participants 컬렉션에 추가
                participant_data = {
                    'post_id': result.inserted_id,
                    'user_id': ObjectId(author_id),
                    'portion': data['my_portion'],
                    'amount': (data['total_price'] / data['total_portion']) * data['my_portion'],
                    'status': '확정',
                    'created_at': current_time,
                    'updated_at': current_time
                }
                
                db.participants.insert_one(participant_data)
                return make_json_response(True, '게시글 생성에 성공했습니다.', {'post_id': str(result.inserted_id), 'redirect_url': '/'})
            else:
                return make_json_response(False, '게시글 생성에 실패했습니다.', {}), 500
                
        except ValueError as e:
            return make_json_response(False, f'잘못된 데이터 형식: {str(e)}', {}), 400
        
        except Exception as e:
            return make_json_response(False, f'서버 오류: {str(e)}', {}), 500            
            
    return render_template('blog/create.html')

# TODO : 전체 리스트 요청 
# @bp.route('/posts', methods=('GET'))
# @login_required
# def get_post_list():
#     db = get_db()
#     try:
        

@bp.route('/posts/<id>', methods=['GET'])
@login_required
def get_post(id, check_author=True):
    db = get_db()
    try:
        # ObjectId 유효성 검사
        if not ObjectId.is_valid(id):
            abort(404, "Invalid post ID format")
            
        post = db.posts.aggregate([
            {
                "$match": {"_id": ObjectId(id)}
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
                "$unwind": {
                    "path": "$author",
                    "preserveNullAndEmptyArrays": True
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
                "$lookup": {
                    "from": "users",
                    "localField": "participants.user_id",
                    "foreignField": "_id",
                    "as": "participant_users"
                }
            },
            {
                "$addFields": {
                    "participants": {
                        "$map": {
                            "input": "$participants",
                            "as": "participant",
                            "in": {
                                "$mergeObjects": [
                                    "$$participant",
                                    {
                                        "username": {
                                            "$let": {
                                                "vars": {
                                                    "user": {
                                                        "$arrayElemAt": [
                                                            {
                                                                "$filter": {
                                                                    "input": "$participant_users",
                                                                    "cond": {
                                                                        "$eq": ["$$this._id", "$$participant.user_id"]
                                                                    }
                                                                }
                                                            },
                                                            0
                                                        ]
                                                    }
                                                },
                                                "in": "$$user.username"
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            },
            {
                "$project": {
                    "id": "$_id",
                    "title": 1,
                    "content": 1,
                    "store_name": 1,
                    "menus": 1,
                    "total_price": 1,
                    "my_portion": 1,
                    "total_portion": 1,
                    "deadline": 1,
                    "status": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "participants": 1,
                    "author_id": 1,
                    "url": 1,
                    "author_name": {"$ifNull": ["$author.username", "알 수 없음"]},
                    "remaining_portion": {
                        "$subtract": [
                            "$total_portion",
                            {"$sum": "$participants.portion"}
                        ]
                    }
                }
            }
        ]).try_next()

        if post is None:
            abort(404, f"Post id {id} doesn't exist.")

        if request.method == 'GET':
            return render_template('blog/detail.html', post=post)
        return post
        
    except Exception as e:
        current_app.logger.error(f"Error fetching post {id}: {str(e)}")
        abort(404, f"Error fetching post: {str(e)}")


@bp.route('/update/<id>', methods=['GET', 'POST'])
@login_required
def update(id):
    db = get_db()

    post = db.posts.aggregate([
        {
            "$match": {"_id": ObjectId(id)}
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
            "$unwind": {
                "path": "$author",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$project": {
                "id": "$_id",
                "title": 1,
                "content": 1,
                "store_name": 1,
                "menus": 1,
                "total_price": 1,
                "my_portion": 1,
                "total_portion": 1,
                "deadline": 1,
                "status": 1,
                "created_at": 1,
                "participants": 1,
                "author_id": 1,
                "author_name": {"$ifNull": ["$author.username", "알 수 없음"]}
            }
        }
    ]).try_next()

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if post['author_id'] != ObjectId(g.user['_id']):
        abort(403, "You don't have permission to edit this post.")

    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # 필수 필드 검증
            required_fields = ['title', 'store_name', 'menus', 'content', 'total_price', 'my_portion', 'total_portion', 'deadline']
            for field in required_fields:
                if not data.get(field):
                    return make_json_response(False, f'{field} is required.', {}), 400

            updated_data = {
                'title': data['title'],
                'store_name': data['store_name'],
                'menus': data['menus'],
                'content': data['content'],
                'total_price': int(data['total_price']),
                'my_portion': int(data['my_portion']),
                'total_portion': int(data['total_portion']),
                'deadline': datetime.strptime(data['deadline'], "%Y-%m-%dT%H:%M"),
                'updated_at': get_korea_time(),
                'url': data.get('url', '').strip()
            }

            result = db.posts.update_one(
                {'_id': ObjectId(id), 'author_id': ObjectId(g.user['_id'])},
                {'$set': updated_data}
            )

            if result.modified_count > 0:
                return make_json_response(True, '게시글이 성공적으로 수정되었습니다.', {'redirect_url': '/'})
            else:
                return make_json_response(False, '게시글 수정에 실패했습니다.', {}), 400

        except ValueError as e:
            return make_json_response(False, f'잘못된 데이터 형식: {str(e)}', {}), 400
        except Exception as e:
            current_app.logger.error(f"Error updating post {id}: {str(e)}")
            return make_json_response(False, f'서버 오류가 발생했습니다.', {}), 500

    return render_template('blog/update.html', post=post)



@bp.route('/delete/<id>', methods=['POST'])
@login_required
def delete(id):
    try:
        # get_post(id, check_author=True)
        
        db = get_db()
        result = db.posts.delete_one({'_id': ObjectId(id), 'author_id': ObjectId(g.user['_id'])})

        if result.deleted_count > 0:
            return make_json_response(True, '게시글 삭제에 성공했습니다.', {'redirect_url': '/'})
        else:
            return make_json_response(False, '게시글 삭제에 실패했습니다.', {}), 400
            
    except Exception as e:
        return make_json_response(False, str(e), {}), 404

@bp.route('/detail/<id>', methods=['GET', 'POST'])
@login_required
def detail(id):
    post = get_post(id, check_author=False)    
    return render_template('/blog/detail.html', post=post)
