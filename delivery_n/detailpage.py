from datetime import datetime
import math
from flask import Blueprint, render_template, request, g
from bson.objectid import ObjectId
from .db import get_db 
from .utils import make_json_response 
from .auth import login_required 
from flask import jsonify

bp = Blueprint('post_detail', __name__, url_prefix='/post')

@bp.route('/<post_id>/participant/<user_id>/accept', methods=['PATCH'])
@login_required
def accept_participant(post_id, user_id):
    db = get_db()
    post = db.posts.find_one({"_id": ObjectId(post_id)})
    if not post or str(post['author_id']) != str(g.user['_id']):
        return make_json_response(False, "권한이 없습니다."), 403
    
    participant = db.participants.find_one({"post_id": ObjectId(post_id), "user_id": ObjectId(user_id)})
    if not participant:
        return make_json_response(False, "참여자를 찾을 수 없습니다."), 404
    
    db.participants.update_one(
        {"post_id": ObjectId(post_id), "user_id": ObjectId(user_id)},
        {"$set": {"status": "확정", "updated_at": datetime.now()}}
    )
    return make_json_response(True, "수락 완료")

@bp.route('/<post_id>/participant/<user_id>/reject', methods=['PATCH'])
@login_required
def reject_participant(post_id, user_id):
    db = get_db()
    post = db.posts.find_one({"_id": ObjectId(post_id)})
    if not post or str(post['author_id']) != str(g.user['_id']):
        return make_json_response(False, "권한이 없습니다."), 403
    
    participant = db.participants.find_one({"post_id": ObjectId(post_id), "user_id": ObjectId(user_id)})
    if not participant:
        return make_json_response(False, "참여자를 찾을 수 없습니다."), 404
    
    db.participants.update_one(
        {"post_id": ObjectId(post_id), "user_id": ObjectId(user_id)},
        {"$set": {"status": "취소", "updated_at": datetime.now()}}
    )
    return make_json_response(True, "거절 완료")

@bp.route('/join/<post_id>', methods=['POST'])
@login_required
def join_post(post_id):
    try:
        db = get_db()
        portion = request.json.get('portion')
        if not isinstance(portion, int) or portion < 1:
            return make_json_response(False, "유효한 참여 수량을 입력해주세요."), 400

        post = db.posts.find_one({"_id": ObjectId(post_id)})
        if not post:
            return make_json_response(False, "게시글이 존재하지 않습니다."), 404

        my_id = ObjectId(g.user['_id'])
        if my_id == post['author_id']:
            return make_json_response(False, "작성자는 참여할 수 없습니다."), 400

        with db.client.start_session() as session:
            with session.start_transaction():
                existing_participants = list(db.participants.find({"post_id": ObjectId(post_id)}))
                total_used_portion = sum(p.get('portion', 0) for p in existing_participants)
                max_portion = post.get('total_portion', 1)

                if any(p['user_id'] == my_id for p in existing_participants):
                    return make_json_response(False, "이미 참여하셨습니다."), 400

                remaining_portion = max_portion - total_used_portion
                if portion > remaining_portion:
                    return make_json_response(False, f"남은 참여 수량은 {remaining_portion}명입니다."), 400

                unit_price = math.ceil(post.get('total_price', 0) / max_portion)
                amount = unit_price * portion

                new_participant = {
                    "post_id": ObjectId(post_id),
                    "user_id": my_id,
                    "portion": portion,
                    "amount": amount,
                    "status": "대기",
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                result = db.participants.insert_one(new_participant, session=session)

                return make_json_response(True, "참여가 완료되었습니다.")

    except Exception as e:
        return make_json_response(False, f"오류가 발생했습니다: {str(e)}"), 500
    

@bp.route('/<post_id>', methods=['GET'])
@login_required
def post_detail(post_id):
    db = get_db()
    post = db.posts.find_one({"_id": ObjectId(post_id)})
    if not post:
        return make_json_response(False, "게시글을 찾을 수 없습니다."), 404

    participants = list(db.participants.find({"post_id": ObjectId(post_id)}))
    for p in participants:
        user = db.users.find_one({"_id": p['user_id']})
        p['username'] = user['username'] if user else "알 수 없음"

    total_used_portion = sum(p['portion'] for p in participants)
    remaining_portion = post.get('total_portion', 1) - total_used_portion

    return render_template('blog.detail.html', post=post, participants=participants, remaining_portion=remaining_portion)