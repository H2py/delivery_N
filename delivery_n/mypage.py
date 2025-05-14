from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g, jsonify
from datetime import datetime
from werkzeug.exceptions import abort
from werkzeug.security import generate_password_hash
from .auth import login_required
from .db import get_db
from bson.objectid import ObjectId
from .utils import make_response

bp = Blueprint('mypage', __name__, url_prefix='/mypage')

@bp.route('/modify_name', methods=['GET', 'POST'])
@login_required
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
@login_required
def modify_password():
    return redirect(url_for('auth.recover'))


@bp.route('/my_posts', methods=['GET'])
@login_required
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