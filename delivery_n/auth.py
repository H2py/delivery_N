import functools
from flask import Blueprint, flash, g, redirect, render_template, request, url_for, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from pymongo import MongoClient
from .db import get_db
from flask_jwt_extended import create_access_token, get_jwt_identity, set_access_cookies, set_refresh_cookies, unset_jwt_cookies, verify_jwt_in_request, create_refresh_token
from bson.objectid import ObjectId
from .email import send_mail
import random
from datetime import datetime, timedelta
from .utils import make_json_response
from flask import make_response  

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
            
        otp_record = db.otp_tokens.find_one({'email': email})
        if otp_record is None:
            error = '인증 요청을 먼저 해주세요.'
        elif not otp_record.get('verified', False):
            error = '이메일 인증이 완료되지 않았습니다.'
        
        if error is None:
            try:
                user_id = db.users.insert_one({
                    'username': username,
                    'email': email,
                    'password': generate_password_hash(password)
                }).inserted_id
                db.otp_tokens.delete_one({'email': email})

                access_token = create_access_token(identity=str(user_id), expires_delta=timedelta(minutes=30))
                refresh_token = create_refresh_token(identity=str(user_id), expires_delta=timedelta(days=14))

                response = make_response(redirect(url_for('index')))
                set_access_cookies(response, access_token, max_age=30*60)  
                set_refresh_cookies(response, refresh_token, max_age=14*24*60*60) 
                db.tokens.update_one(
                    {'user_id': user_id},
                    {'$set': {
                        'token': refresh_token,
                        'created_at': datetime.now(),
                        'expired_at': datetime.now() + timedelta(days=14),
                        'is_revoked': False
                    }},
                    upsert=True
                )
                      
                return response

            except Exception as e:
                error = f"Registration failed: {e}"

    return render_template('auth/register.html')


@bp.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return make_json_response(False, "이메일이 필요합니다.")
    
    db = get_db()
    if db.users.find_one({'email': email}):
        return make_json_response(False, "이미 가입된 이메일입니다.")

    otp = str(random.randint(100000, 999999))
    expires_at = datetime.now() + timedelta(minutes=5)
    db.otp_tokens.delete_one({'email': email})
    db.otp_tokens.insert_one({
        'email': email,
        'otp': otp,
        'created_at': datetime.now(),
        'expires_at': expires_at,
        'verified': False
    })

    if send_mail(email, otp):
        return make_json_response(True, "인증 코드가 전송되었습니다.")
    else:
        return make_json_response(False, "이메일 전송에 실패했습니다.")

@bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')

    if not email or not otp:
        return make_json_response(False, "이메일, 인증코드가 필요합니다.")

    db = get_db()
    otp_record = db.otp_tokens.find_one({'email': email})

    if not otp_record:
        return make_json_response(False, "인증코드가 존재하지 않습니다.")

    if datetime.now() > otp_record['expires_at']:
        db.otp_tokens.delete_one({'email': email})
        return make_json_response(False, "인증코드가 만료되었습니다.")

    if otp != otp_record['otp']:
        return make_json_response(False, "인증 코드가 일치하지 않습니다.")

    db.otp_tokens.update_one(
        {'email': email},
        {'$set': {'verified': True}}
    )
    return make_json_response(True, "인증이 완료되었습니다.")


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.users.find_one({'email': email}) 
        
        if user is None:
            error = 'Incorrect email' 
        elif not check_password_hash(user['password'], password):
            error = "Incorrect password."
            
        if error is None:
            access_token = create_access_token(identity=str(user['_id']), expires_delta= timedelta(minutes=30))
            refresh_token = create_refresh_token(identity=str(user['_id']), expires_delta = timedelta(days=14))
            
            db.tokens.update_one(
                {'user_id' : user['_id']},
                {'$set':{
                    'token': refresh_token,
                    'created_at' : datetime.now(),
                    'expired_at' : datetime.now() + timedelta(days=14),
                    'is_revoked' : False
                }},
                upsert=True
            )
            response = redirect(url_for('blog.index'))
            response.set_cookie('access_token_cookie', access_token, httponly=True, secure=False)
            response.set_cookie('refresh_token_cookie', refresh_token, httponly=True, secure=False)
            return response
        
        flash(error)
        
    return render_template('auth/login.html')

@bp.route('/recover', methods=('GET', 'POST'))
def recover():
    if request.method == 'POST':
        email = request.form['email']
        db = get_db()
        otp = str(random.randint(100000, 999999)) 
        error = None
        
        user = db.users.find_one({'email': email})
        if user is None:
            error = '등록된 이메일이 없습니다.'
        
        if error is None:
            if send_mail(email, otp):
                flash('비밀번호 재설정 링크를 이메일로 보냈습니다.')
            else:
                flash('이메일 전송에 실패했습니다. 다시 시도해주세요/')
            return redirect(url_for('auth.login'))
        
        flash(error)
    
    return render_template('auth/recover.html')

@bp.before_app_request
def load_logged_in_user():
    g.user = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            db = get_db()
            g.user = db.users.find_one({'_id': ObjectId(user_id)})
    except Exception:
        g.user = None
        
@bp.route('/logout')
def logout():
    db = get_db()
    user_id = get_jwt_identity()
    db.tokens.update_one(
        {'user_id': ObjectId(user_id), 'is_revoked': False},
        {'$set': {'is_revoked': True, 'revoked_at': datetime.now()}}
    )
    
    response = make_response(make_json_response(
        True,
        "로그아웃 성공",
        {"redirect_url": url_for('auth.login')}
    ))
    unset_jwt_cookies(response)
    
    return response, 200

@bp.route('/mypage', methods=('GET', 'POST'))
@login_required
def mypage():
    return render_template('mypage/mypage.html')
