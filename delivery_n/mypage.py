from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g, jsonify
from datetime import datetime
from werkzeug.exceptions import abort
from werkzeug.security import generate_password_hash, check_password_hash
from .auth import login_required
from .db import get_db
from werkzeug.security import generate_password_hash, 
from bson.objectid import ObjectId
from .utils import make_response

bp = Blueprint('mypage', __name__, url_prefix='/mypage')

@bp.route('/modify_name', methods=['GET', 'POST'])
# @login_required
def modify_name():
    db = get_db()
    if request.method == 'POST':
        new_username = request.form.get('username')
        error = None

        if not new_username:
            error = '닉네임을 입력해주세요.'
        elif len(new_username) > 20:
            error = '닉네임은 20자 이내여야 합니다.'

        if error:
             return make_response(False, error)

        db.users.update_one(
            {"_id": ObjectId(g.user['_id'])},
            {"$set": {"username": new_username}}
        )
        g.user['username'] = new_username  
        return make_response(True, "닉네임이 성공적으로 변경되었습니다.")


    return render_template('mypage/mypage.html')


@bp.route('/modify_password', methods=['GET', 'POST'])
# @login_required
def modify_password():
    db = get_db()

    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        user = db.users.find_one({'_id': ObjectId(g.user['_id'])})

        if not current_password or not check_password_hash(user['password'], current_password):
            return make_response(False, "현재 비밀번호가 일치하지 않습니다.")
        if not new_password or not confirm_password:
            return make_response(False, "새 비밀번호와 확인칸 모두 입력해주세요.")
        if new_password != confirm_password:
            return make_response(False, "새 비밀번호가 일치하지 않습니다.")
        if len(new_password) < 5:
            return make_response(False, "새 비밀번호는 5자 이상이어야 합니다.")
        if check_password_hash(user['password'], new_password):
            return make_response(False, "기존 비밀번호와 다른 비밀번호를 입력해주세요.")
     
        db.users.update_one(
            {"_id": ObjectId(g.user['_id'])},
            {"$set": {"password": generate_password_hash(new_password)}}
        )
        return make_response(True, "비밀번호가 성공적으로 변경되었습니다.")

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

    return make_response(True, "내 게시글 목록입니다.", posts)

@bp.route('/delete_account', methods=['POST'])
# @login_required
def delete_account():
    db = get_db()
    db.users.update_one(
        {'_id': ObjectId(g.user['_id'])},
     {'$set': {'deleted_at': True}} 
    )
    return redirect(url_for('index'))