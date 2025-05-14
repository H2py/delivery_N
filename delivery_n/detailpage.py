import math
from flask import Blueprint, request, g
from bson.objectid import ObjectId
from .db import get_db 
from .utils import make_json_response 
from .auth import login_required 
from flask import jsonify

bp = Blueprint('post_detail', __name__, url_prefix='/post')

#수락버튼
@bp.route('/<post_id>/participant/<user_id>/accept', methods=['PATCH'])
@login_required
def accept_participant(post_id, user_id):
    db = get_db()
    post = db.posts.find_one({"_id": ObjectId(post_id)})
    if not post or str(post['author_id']) != str(g.user['_id']):
        return make_json_response(False, "권한이 없습니다.")
    
    db.posts.update_one(
        {"_id": ObjectId(post_id), "participants.user_id": ObjectId(user_id)},
        {"$set": {"participants.$.status": "confirmed"}}
    )
    return make_json_response(True, "수락 완료")

#거절버튼
@bp.route('/<post_id>/participant/<user_id>/reject', methods=['PATCH'])
@login_required
def reject_participant(post_id, user_id):
    db = get_db()
    post = db.posts.find_one({"_id": ObjectId(post_id)})
    if not post or str(post['author_id']) != str(g.user['_id']):
        return make_json_response(False, "권한이 없습니다.")
    
    db.posts.update_one(
        {"_id": ObjectId(post_id), "participants.user_id": ObjectId(user_id)},
        {"$set": {"participants.$.status": "cancelled"}}
    )
    return make_json_response(True, "거절 완료")

#참여하기
@bp.route('/join/<post_id>', methods=['POST'])
@login_required
def join_post(post_id):
    try:
        db = get_db()
        portion = request.json.get('portion')

        post = db.posts.find_one({"_id": ObjectId(post_id)})
        if not post:
            return make_json_response(False, "게시글이 존재하지 않습니다."), 404

        my_id = ObjectId(g.user['_id'])

        # participants 컬렉션에서 해당 post_id를 가진 모든 참여자의 portion 합계 계산
        existing_participants = db.participants.find({"post_id": ObjectId(post_id)})
        total_used_portion = sum(p.get('portion', 0) for p in existing_participants)
        max_portion = post.get('total_portion', 1)

        # 이미 참여한 사람인지 확인
        if db.participants.find_one({"post_id": ObjectId(post_id), "user_id": my_id}):
            return make_json_response(False, "이미 참여하셨습니다."), 400

        # 예상 금액 계산 (올림 처리)
        unit_price = math.ceil(post.get('total_price', 0) / max_portion)
        amount = unit_price * portion

        from datetime import datetime
        now = datetime.utcnow()

        # 새로운 참여자 데이터 생성
        new_participant = {
            "post_id": ObjectId(post_id),
            "user_id": my_id,
            "portion": portion,
            "amount": amount,
            "status": "대기",
            "created_at": now,
            "updated_at": now
        }

        # 참여자 정보 추가
        result = db.participants.insert_one(new_participant)

        if result.inserted_id:
            return make_json_response(True, "참여가 완료되었습니다.")
        else:
            return make_json_response(False, "참여 처리 중 오류가 발생했습니다."), 500

    except Exception as e:
        return make_json_response(False, f"오류가 발생했습니다: {str(e)}"), 500