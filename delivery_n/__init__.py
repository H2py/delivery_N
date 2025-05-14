from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient
import os

from flask_jwt_extended import JWTManager

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev'), 
        MONGO_URI='mongodb://localhost:27017/delivery',
        JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY', 'dev')
    )
    
    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)
    
    JWTManager(app)
    
    from . import db
    db.init_db(app)
    
    from . import auth
    app.register_blueprint(auth.bp)
    
    from . import blog
    app.register_blueprint(blog.bp)
    app.add_url_rule('/', endpoint="index")
    
    from . import api
    app.add.register_blueprint(api.bp)
    
    return app
        