import functools
from flask import (Blueprint, flash, g, redirect, render_template, request, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from pymongo import MongoClient
from .db import get_db
from flask_jwt_extended import create_access_token, get_jwt_identity
from bson.objectid import ObjectId

bp = Blueprint('auth', __name__, url_prefix='/auth')

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        db = get_db()
        error = None
        
        if not username:
            error = 'Username is required'
        elif not password:
            error = 'Password is required'    
        elif not email:
            error = 'Email is required'
        elif db.users.find_one({'username': username}):
            error = 'Username already exists'
        elif db.users.find_one({'email': email}):
            error = 'Email already exists'
            
        if error is None:
            try:
                db.users.insert_one({
                    'username': username,
                    'email': email,
                    'password': generate_password_hash(password)
                })
                return redirect(url_for('auth.login'))
            except Exception as e:
                error = f"Registration failed: {e}"

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
            access_token = create_access_token(identity=str(user['_id']))
            response = redirect(url_for('blog.index'))
            # secure=True로 설정하면 HTTPS에서만 쿠키가 전송됨
            response.set_cookie('access_token', access_token, httponly=True, secure=False)
            return response
        
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
    token = request.cookies.get('access_token')
    
    if not token:
        g.user = None
        return
    try:
        user_id = get_jwt_identity()
        if user_id:
            db = get_db()
            g.user = db.users.find_one({'_id': ObjectId(user_id)}) 
        else:
            g.user = None
    except:
        g.user = None
        
@bp.route('/logout')
def logout():
    response = redirect(url_for('auth.login'))
    response.delete_cookie('access_token')
    return response


@bp.route('/mypage', methods=('GET', 'POST'))
@login_required
def mypage():
    return render_template('mypage/mypage.html')
