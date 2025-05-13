from flask import Flask, render_template
from pymongo import MongoClient

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        MONGO_URI='mongodb://localhost:27017/delivery'
    )
    
    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)
    
    from . import db
    db.init_db(app)
    
    from . import auth
    app.register_blueprint(auth.bp)
    

    return app
        