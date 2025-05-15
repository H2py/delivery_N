import functools
from flask import Blueprint, flash, g, json, redirect, render_template, request, url_for, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from pymongo import MongoClient
from .db import get_db
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, set_access_cookies, set_refresh_cookies, unset_jwt_cookies, verify_jwt_in_request, create_refresh_token
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
        elif db.users.find_one({'username': username, 'is_active': True}):
            error = 'Username already exists'
        elif db.users.find_one({'email': email, 'is_active': True}):
            error = 'Email already exists'
        
        otp_record = db.otp_tokens.find_one({'email': email})
        if otp_record is None:
            error = '인증 요청을 먼저 해주세요.'
        elif not otp_record.get('verified', False):
            error = '이메일 인증이 완료되지 않았습니다.'
        
        if error is None:
            try:
                existing_user = db.users.find_one({
                    'email': email,
                    'is_active': False,        
                })                
                if existing_user:
                    db.users.update_one(
                        {'_id': existing_user['_id']},
                        {
                            '$set': {
                                'username': username,
                                'password': generate_password_hash(password),
                                'deleted_at': None,
                                'updated_at': datetime.now(),
                                'is_active': True,
                            },
                            '$unset': {'revoked_at': ''}  
                        }
                    )
                    user_id = existing_user['_id']
                else:
                    user_id = db.users.insert_one({
                        'username': username,
                        'email': email,
                        'password': generate_password_hash(password),
                        'deleted_at': None,
                        'created_at': datetime.now(),
                        'updated_at': None,
                        "is_active": True,
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
                flash(error)
        
        flash(error)
    
    return render_template('auth/register.html')


@bp.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return make_json_response(False, "이메일이 필요합니다.")
    
    db = get_db()
    if db.users.find_one({'email': email, 'is_active': True}):
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

    if send_mail(
        email, 
        '[같이먹자] 이메일 인증 번호', 
        f'인증 번호를 입력하여 이메일 인증을 완료해 주세요.\n인증 번호: {otp}'):
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


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            data = request.get_json()  
            email = data.get('email')
            password = data.get('password')
            
            if not email or not password:
                return make_json_response(False, "이메일과 비밀번호를 입력해주세요."), 400
            
            db = get_db()
            user = db.users.find_one({'email': email})
            
            if user is None:
                return make_json_response(False, "등록된 이메일이 없습니다."), 401
            
            # is_active가 False인 경우 체크
            #if user.get('is_active') is False:
                #return make_json_response(False, "탈퇴한 계정입니다."), 401
            
            elif not check_password_hash(user['password'], password):
                return make_json_response(False, "비밀번호가 일치하지 않습니다."), 401
            
            access_token = create_access_token(
                identity=str(user['_id']),
                expires_delta=timedelta(minutes=30)
            )
            refresh_token = create_refresh_token(
                identity=str(user['_id']),
                expires_delta=timedelta(days=14)
            )
            
            db.tokens.update_one(
                {'user_id': user['_id']},
                {'$set': {
                    'token': refresh_token,
                    'created_at': datetime.now(),
                    'expired_at': datetime.now() + timedelta(days=14),
                    'is_revoked': False
                }},
                upsert=True
            )
            
            response = make_response(make_json_response(
                True, "로그인 성공", {"redirect_url": url_for('blog.index')}
            ))
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            return response
        
        except Exception as e:
            error_message = f"서버 오류가 발생했습니다: {str(e)}"
            print(error_message)  
            return make_json_response(False, error_message), 500
    
    return render_template('auth/login.html')


@bp.route('/recover', methods=['GET', 'POST'])
def recover():
    if request.method == 'POST':
        try:
            data = request.get_json()
            email = data.get('email')
            
            if not email:
                return make_json_response(False, "이메일을 입력해주세요.")
            
            db = get_db()
            user = db.users.find_one({'email': email, 'deleted_at': {'$ne': True}})
            
            if user is None:
                return make_json_response(False, "등록되지 않은 이메일입니다.")
            
            # 6자리 랜덤 숫자 생성
            new_password = str(random.randint(100000, 999999))
            
            # 이메일 전송
            email_content = f"""
                안녕하세요, 같이먹자입니다.
                요청하신 새로운 비밀번호입니다: {new_password}

                보안을 위해 로그인 후 비밀번호를 변경해주세요.
            """
            if not send_mail(
                email, 
                '[같이먹자] 임시 비밀번호 안내', 
                email_content):
                return make_json_response(False, "이메일 전송에 실패했습니다. 잠시 후 다시 시도해주세요.")
            
            # 새 비밀번호 암호화 및 DB 업데이트
            hashed_password = generate_password_hash(new_password)
            db.users.update_one(
                {'_id': user['_id']},
                {'$set': {'password': hashed_password}}
            )
            
            return make_json_response(True, "새로운 비밀번호가 이메일로 전송되었습니다.")
            
        except Exception as e:
            print(f"비밀번호 재설정 중 오류 발생: {str(e)}")
            return make_json_response(False, "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
    
    return render_template('auth/recover.html')

@bp.before_app_request
def load_logged_in_user():
    g.user = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        
        if user_id:
            db = get_db()
            user = db.users.find_one({'_id': ObjectId(user_id)})
            
            token_valid = db.tokens.find_one({
                'user_id': ObjectId(user_id),
                'is_revoked': False,
                'expired_at': {'$gt': datetime.now()}
            })
            
            if user and token_valid:
                g.user = user
            else:
                g.user = None
                if not token_valid and hasattr(request, 'cookies') and ('access_token_cookie' in request.cookies or 'refresh_token_cookie' in request.cookies):
                    g.clear_jwt_cookies = True
    except Exception as e:
        print(f"사용자 인증 중 오류: {str(e)}")
        g.user = None


@bp.route('/logout', methods=['POST'])
def logout():
    db = get_db()
    
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            db.tokens.update_one(
                {'user_id': ObjectId(user_id), 'is_revoked': False},
                {'$set': {'is_revoked': True, 'revoked_at': datetime.now()}}
            )
    except Exception as e:
        print(f"로그아웃 중 오류: {str(e)}")

    response = make_response()
    response.delete_cookie('access_token_cookie', path='/')
    response.delete_cookie('refresh_token_cookie', path='/')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response.set_data(json.dumps({
            'success': True,
            'data': {'redirect_url': url_for('auth.login')}
        }))
        response.headers['Content-Type'] = 'application/json'
        return response, 200

    response.status_code = 302
    response.headers['Location'] = url_for('auth.login')
    return response


@bp.route('/mypage', methods=['GET', 'POST'])
# @login_required
def mypage():
    return render_template('mypage/mypage.html')
