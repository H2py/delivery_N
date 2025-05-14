from datetime import datetime
from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from .auth import login_required
from .db import get_db
from bson.objectid import ObjectId

bp = Blueprint('blog', __name__)

@bp.route('/')
def index():
    db = get_db()
    posts = db.posts.aggregate([
        {
            "$lookup": {
                "from": "users",
                "localField": "author_id",
                "foreignField": "_id",
                "as": "author"
            }
        },
        {
            "$unwind": "$author"
        },
        {
            "$project": {
                "id": "$_id",
                "title": 1,
                "body": 1,
                "created": 1,
                "author_id": 1,
                "username": "$author.username"
            }
        },
        {
            "$sort": {"created": -1}
        }
    ])
    posts_list = list(posts)
    return render_template('blog/index.html', posts=posts_list)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        url = request.form.get('url') 

        db = get_db()
        error = None

        if not title:
            error = 'Title is required.'
        
        if error is not None:
            flash(error)
        else:
            db.posts.insert_one({
                'title': title,
                'body': body,
                'url': url,  # ← DB에 url 저장 추가
                'created': datetime.now(),
                'author_id': ObjectId(g.user['_id'])
            })
            return redirect(url_for('blog.index'))
    return render_template('blog/create.html')
                
def get_post(id, check_author=True):
    db = get_db()
    try:
        post = db.posts.aggregate([
            {
                "$match": {"_id": ObjectId(id)}
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "author_id",
                    "foreignField": "_id",
                    "as": "author"
                }
            },
            {
                "$unwind": "$author"
            },
            {
                "$project": {
                    "id": "$_id",
                    "title": 1,
                    "body": 1,
                    "created": 1,
                    "author_id": 1,
                    "username": "$author.username"
                }
            }
        ]).next()  
    except (StopIteration, ValueError):
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post['author_id'] != ObjectId(g.user['_id']):
        abort(403)

    return post
    
    
@bp.route('/<int:id>/update', methods=['GET', 'POST'])
@login_required
def update(id):
    post = get_post(id)
    
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

    if not title:
            error = 'Title is required.'

    if error is not None:
            flash(error)
    else:
        db = get_db()
        db.posts.insert_one({
            'title': title,
            'body': body,
            'created': datetime.now(),
            'author_id': ObjectId(g.user['_id'])
        })
        return redirect(url_for('blog.index'))
    return render_template('blog/update.html', post=post)



@bp.route('/<int:id>/delete', methods=['POST'])
# @login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.posts.insert_one({
        'created': datetime.now(),
        'author_id': ObjectId(g.user['_id'])
    })
    return redirect(url_for('blog.index'))
