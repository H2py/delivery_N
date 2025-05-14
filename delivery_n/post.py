from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from datetime import datetime
from .utils import get_next_sequence
from werkzeug.exceptions import abort
from .auth import login_required
from .db import get_db
from bson.objectid import ObjectId

bp = Blueprint('posts', __name__)

#홈화면 게시글 보이기
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
        {"$unwind": "$author"},
        {
            "$project": {
                "id": "$_id",
                "title": 1,
                "store": 1,
                "menu": 1,
                "content": 1,
                "portion": 1,
                "people": 1,
                "totalPrice": 1,
                "deadline": 1,
                "created_at": 1,
                "username": "$author.username"
            }
        },
        {"$sort": {"created_at": -1}}
    ])
    return render_template('mainpage.html', posts=list(posts))

#게시글 포스팅
@bp.route('/write', methods=['GET', 'POST'])
@login_required
def write():
    if request.method == 'POST':
        title = request.form.get('title')
        store = request.form.get('store')
        menu = request.form.get('menu')
        content = request.form.get('content')
        portion = request.form.get('portion')
        people = request.form.get('people')
        totalPrice = request.form.get('totalPrice')
        deadline = request.form.get('deadline')
        url = request.form.get('url')

        error = None

        if not title:
            error = '제목을 입력해주세요.'
        elif not store:
            error = '가게 이름을 입력해주세요.'
        elif not menu:
            error = '메뉴를 입력해주세요.'
        elif not content:
            error = '내용을 입력해주세요.'
        elif not portion:
            error = '1인분 가격을 입력해주세요.'
        elif not people:
            error = '모집 인원을 입력해주세요.'
        elif not totalPrice:
            error = '총 금액을 입력해주세요.'
        elif not deadline:
            error = '마감 시간을 입력해주세요.'

        if error is None:
            try:
                db = get_db()
                post_number = get_next_sequence(db, "post_id")

                portion_int = int(portion)
                amount = portion_int  # 본인이 portion 1개 가져간다고 가정

                post = {
                    "number": post_number,
                    "title": title,
                    "store": store,
                    "menu": menu,
                    "content": content,
                    "portion": portion_int,
                    "people": int(people),
                    "totalPrice": int(totalPrice),
                    "deadline": deadline,
                    "url": url,
                    "created_at": datetime.now(),
                    "author_id": ObjectId(g.user['_id']),
                    "participants": [
                        {
                            "user_id": ObjectId(g.user['_id']),
                            "portion": 1,
                            "amount": amount,
                            "status": "confirmed"
                        }
                    ]
                }

                db.posts.insert_one(post)
                return redirect(url_for('posts.index'))
            except ValueError:
                error = '숫자 항목에 올바른 값을 입력해주세요.'

        return render_template(
            'write.html',
            error=error,
            title=title,
            store=store,
            menu=menu,
            content=content,
            portion=portion,
            people=people,
            totalPrice=totalPrice,
            deadline=deadline,
            url=url
        )

    return render_template('write.html')



#게시글 조회
def get_post(post_id, check_author=True):
    db = get_db()
    try:
        post = db.posts.aggregate([
            {"$match": {"_id": ObjectId(post_id)}},
            {"$lookup": {
                "from": "users",
                "localField": "author_id",
                "foreignField": "_id",
                "as": "author"
            }},
            {"$unwind": "$author"},
            {"$project": {
                "id": "$_id",
                "title": 1,
                "content": 1,
                "created_at": 1,
                "author_id": 1,
                "username": "$author.username",
                "store": 1,
                "menu": 1,
                "deadline": 1,
                "portion": 1,
                "people": 1,
                "totalPrice": 1,
                "url": 1,
                "participants": 1  # ← 참여자 정보도 필요
            }}
        ]).next()
    except (StopIteration, ValueError):
        abort(404, f"Post id {post_id} doesn't exist.")

    if check_author and post['author_id'] != ObjectId(g.user['_id']):
        abort(403)
    return post

#게시글 수정
@bp.route('/<post_id>/update', methods=['GET', 'POST'])
@login_required
def update(post_id):
    post = get_post(post_id)

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        error = None

        if not title:
            error = '제목은 필수입니다.'

        if error:
            flash(error)
        else:
            db = get_db()
            db.posts.update_one(
                {"_id": ObjectId(post_id)},
                {"$set": {
                    "title": title,
                    "content": content,
                    "created_at": datetime.now()
                }}
            )
            return redirect(url_for('posts.index'))

    return render_template('update.html', post=post)


#게시글 삭제
@bp.route('/<post_id>/delete', methods=['POST'])
@login_required
def delete(post_id):
    get_post(post_id)
    db = get_db()
    db.posts.delete_one({"_id": ObjectId(post_id)})
    return redirect(url_for('posts.index'))