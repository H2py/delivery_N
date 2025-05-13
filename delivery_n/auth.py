import functools

from flask import (Blueprint, flash, g, redirect, render_template, request, session,
                   url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from pymongo import MongoClient
from .db import get_db
import sys

print(sys.path)

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        
        if not username:
            error = 'Username is required'
        elif not password:
            error = 'Password is required'    
        
        
        if error is None:
            try:
                db.users.insert_one({
                    'username': username,
                    'password': generate_password_hash(password)
                })
                return redirect(url_for('auth.login'))
            except Exception as e:
                error = f"Registration failed: {e}"

        flash(error)
    return render_template('auth/register.html')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.users.find_one({'username': username}) 
        
        if user is None:
            error = 'Incorrect username.' 
        elif not check_password_hash(user['password'], password):
            error = "Incorrect password."
            
        if error is None:
            session.clear()
            session['user_id'] = str(user['_id'])
            return redirect(url_for('index'))
        
        flash(error)
        
    return render_template('auth/login.html')

@bp.route('/recover', methods=('GET', 'POST'))
def recover():
    if request.method == 'POST':
        email = request.form['email']
        db = get_db()
        error = None
        
        user = db.users.find_one({'email': email})
        if user is None:
            error = '등록된 이메일이 없습니다.'
        
        if error is None:
            # 실제로는 여기서 이메일 전송 로직이 필요 (예: 비밀번호 재설정 링크 생성 및 전송)
            # 지금은 테스트용으로 플래시 메시지만 표시
            flash('비밀번호 재설정 링크를 이메일로 보냈습니다.')
            return redirect(url_for('auth.login'))
        
        flash(error)
    
    return render_template('auth/recover.html')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    
    if user_id is None:
        g.user = None
    else:
        from bson.objectid import ObjectId
        db = get_db()
        g.user = db.users.find_one({'_id': ObjectId(user_id)})
        
@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view