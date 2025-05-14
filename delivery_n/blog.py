from datetime import datetime
from flask import Blueprint, flash, g, redirect, render_template, request, url_for, jsonify
from werkzeug.exceptions import abort
from .auth import login_required
from .db import get_db
from bson.objectid import ObjectId

bp = Blueprint('blog', __name__)

@bp.route('/')
def index():
    db = get_db()
    posts = db.posts.aggregate([
        {
            "$lookup": {
                "from": "users",
                "localField": "author_id",
                "foreignField": "_id",
                "as": "author"
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
                }
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
    posts_list = list(posts)
    print("DEBUG: Posts data:", posts_list)
    
    if not posts_list:
        print("DEBUG: No posts found in database")
        posts_list = []

    return render_template('main.html', posts=posts_list)




@bp.route('/create', methods=('GET', 'POST'))
# @login_required
def create():
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # 필수 필드 검증
            required_fields = ['title', 'store_name', 'menus', 'content', 'total_price', 'my_portion', 'total_portion']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({
                        'success': False,
                        'message': f'{field} is required.',
                        'result': {}
                    }), 400

            # 현재 시간
            current_time = datetime.now()
            
            # 데이터베이스에 저장할 문서 생성
            post_data = {
                'title': data['title'],
                'store_name': data['store_name'],
                'menus': data['menus'],
                'content': data['content'],
                'author_id': ObjectId(data['author_id']),  # 프론트엔드에서 전달받은 author_id 사용
                'total_price': data['total_price'],
                'my_portion': data['my_portion'],
                'total_portion': data['total_portion'],
                'deadline': datetime.strptime(data['deadline'], "%Y-%m-%dT%H:%M"),
                'status': '모집중',
                'created_at': current_time,
                'updated_at': current_time
            }
            
            # 데이터베이스에 저장
            db = get_db()
            result = db.posts.insert_one(post_data)
            
            if result.inserted_id:
                return jsonify({
                    'success': True,
                    'message': '게시글 생성에 성공했습니다.',
                    'result': {
                        'redirect_url': '/'
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '게시글 생성에 실패했습니다.',
                    'result': {}
                }), 500
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e),
                'result': {}
            }), 500
            
    return render_template('blog/create.html')
                
def get_post(id, check_author=True):
    db = get_db()
    try:
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
                "$unwind": "$author"
            },
            {
                "$project": {
                    "id": "$_id",
                    "title": 1,
                    "body": 1,
                    "created": 1,
                    "author_id": 1,
                    "username": "$author.username"
                }
            }
        ]).next()  
    except (StopIteration, ValueError):
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post['author_id'] != ObjectId(g.user['_id']):
        abort(403)

    return post
    
    
@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)
    
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

    if not title:
            error = 'Title is required.'

    if error is not None:
            flash(error)
    else:
        db = get_db()
        db.posts.insert_one({
            'title': title,
            'body': body,
            'created': datetime.now(),
            'author_id': ObjectId(g.user['_id'])
        })
        return redirect(url_for('blog.index'))
    return render_template('blog/update.html', post=post)



@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.posts.insert_one({
        'created': datetime.now(),
        'author_id': ObjectId(g.user['_id'])
    })
    return redirect(url_for('blog.index'))
