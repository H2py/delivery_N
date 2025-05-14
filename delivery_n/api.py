from flask import Blueprint, request
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from .db import get_db
from .utils import make_response

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    
    db = get_db()
    user = db.users.find_one({'username': username})
    
    if user is None or not check_password_hash(user['password'], password):
        return make_response(False, "Bad username or password")
    
    access_token = create_access_token(identity=str(user['_id']))
    return make_response(True, "Token issued", [{"access_token": access_token}])

@bp.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    db = get_db()
    user = db.users.find_one({'_id': current_user_id})
    
    if user is None:
        return make_response(False, "User not found")
    
    return make_response(True, "Login successful", [{"username": user['username']}])
