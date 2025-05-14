from datetime import datetime, timedelta, timezone
from bson import ObjectId
from flask import Flask, render_template, jsonify, request
import jwt
from pymongo import MongoClient
import os
from flask_jwt_extended import JWTManager, create_access_token, get_jwt, get_jwt_identity, set_access_cookies
from flask_mail import Mail
from dotenv import load_dotenv

from delivery_n.db import get_db
from delivery_n.utils import refresh_expiring_jwts

mail = Mail()

load_dotenv()

# pip install -r requirements.txt

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev'),
        MONGO_URI=os.getenv('MONGO_URI', 'mongodb://localhost:27017/delivery'),
        JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY', 'dev'),

        MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
        MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
        MAIL_SERVER=os.getenv('MAIL_SERVER', 'smtp.gmail.com'),
        MAIL_PORT=int(os.getenv('MAIL_PORT', 465)),
        MAIL_USE_TLS=os.getenv('MAIL_USE_TLS', 'False').lower() == 'true',
        MAIL_USE_SSL=os.getenv('MAIL_USE_SSL', 'True').lower() == 'true'
    )
    
    app.config.update({
        "JWT_TOKEN_LOCATION": ["cookies"],
        "JWT_ACCESS_COOKIE_NAME": "access_token_cookie",
        "JWT_REFRESH_COOKIE_NAME": "refresh_token_cookie",
        "JWT_COOKIE_SECURE": False,
        "JWT_COOKIE_CSRF_PROTECT": False,
        "JWT_COOKIE_SAMESITE": "Lax"
    })
    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)
    
    mail.init_app(app)
    JWTManager(app)
        
    from . import db
    db.init_db(app)
    
    from . import auth
    app.register_blueprint(auth.bp)
    
    from . import blog
    app.register_blueprint(blog.bp)
    app.add_url_rule('/', endpoint="index")
    
    from . import api
    app.register_blueprint(api.bp)
    
    from . import mypage
    app.register_blueprint(mypage.bp)    

    from . import detailpage
    app.register_blueprint(detailpage.bp)

    app.after_request(refresh_expiring_jwts)


    return app
        