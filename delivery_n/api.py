from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from .db import get_db

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    
    db = get_db()
    user = db.users.find_one({'username': username})
    
    if user is None or not check_password_hash(user['password'], password):
        return jsonify({"msg": "Bad username or password"}), 401

    access_token = create_access_token(identity=str(user['_id']))
    return jsonify(access_token=access_token)

@bp.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    db= get_db()
    user = db.users.find_one({'_id': current_user_id})
    if user is None:
        return jsonify({"msg": "User not found"}, 404)
    return jsonify(logged_in_as=user['username']), 200