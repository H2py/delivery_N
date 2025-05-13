from flask import Flask
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
        
    try:
        client = MongoClient(app.config['MONGO_URI'])
        app.db = client.get_default_database()
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        raise
    
    from . import db
    db.init_app(app)
    
    from . import auth
    app.register_blueprint(auth.bp)
        
    return app
    