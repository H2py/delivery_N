from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient
import os
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from dotenv import load_dotenv

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
        "JWT_COOKIE_SECURE": False,
        "JWT_COOKIE_CSRF_PROTECT": False
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
    
    return app
        