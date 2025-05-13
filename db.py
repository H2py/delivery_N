from pymongo import MongoClient
from datetime import datetime
import click
from flask import current_app, g

def get_db():
    if 'db' not in g:
        g.db=MongoClient(current_app.config['MONGO_URI']).get_default_database()
    
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    
    if db is not None:
        db.close()
        
        
def init_db(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)