from datetime import datetime, timedelta, timezone
from bson import ObjectId
from flask import Blueprint, make_response, request, url_for
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt, jwt_required, get_jwt_identity, set_access_cookies, set_refresh_cookies
from .db import get_db
from .utils import make_json_response

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    
    db = get_db()
    user = db.users.find_one({'username': username})
    
    if user is None or not check_password_hash(user['password'], password):
        return make_json_response(False, "Bad username or password"), 401
    
    access_token = create_access_token(identity=str(user['_id']))
    refresh_token = create_refresh_token(identity=str(user['_id']))
    
    db.tokens.update_one(
        {'user_id': user['_id']},
        {'$set': {
            'token': refresh_token,
            'created_at': datetime.now(timezone.utc),
            'expired_at': datetime.now(timezone.utc) + timedelta(days=14),
            'is_revoked': False
        }},
        upsert=True
    )
    
    response = make_response(make_json_response(
        True,
        "Login successful",
        {"redirect_url": url_for('blog.index')}
    ))
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response

@bp.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    db = get_db()
    user = db.users.find_one({'_id': ObjectId(current_user_id)})
    
    if user is None:
        return make_json_response(False, "User not found"), 404
    
    return make_json_response(True, "Login successful", {"username": user['username']})
