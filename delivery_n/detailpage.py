import math
from flask import Blueprint, request, g
from bson.objectid import ObjectId
from .db import get_db 
from .utils import make_json_response 
from .auth import login_required 
from flask import jsonify

bp = Blueprint('post_detail', __name__, url_prefix='/post')

#DB
@bp.route('/post/<post_id>', methods=['GET'])
@login_required
def get_post_detail(post_id):
    db = get_db()
    post = db.posts.find_one({"_id": ObjectId(post_id)})
    author = db.users.find_one({"_id": post['author_id']})
    
    if not post:
        return jsonify({"success": False, "error": "게시글이 존재하지 않습니다."}), 404

    result = {
        "_id": str(post["_id"]),
        "title": post['title'],
        "store_name": post['store_name'],
        "deadline": post['deadline'].strftime("%Y-%m-%d %H:%M"),
        "menus": post['menus'],
        "content": post['content'],
        "url": post.get("url", ""),
        "total_price": post['total_price'],
        "max_portion": post['max_portion'],
        "participants": post.get('participants', []),
    }

    return jsonify(result)

#수락버튼
@bp.route('/post/<post_id>/participant/<user_id>/accept', methods=['PATCH'])
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
@bp.route('/post/<post_id>/participant/<user_id>/reject', methods=['PATCH'])
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
@bp.route('/post/<post_id>/join', methods=['POST'])
@login_required
def join_post(post_id):
    db = get_db()
    portion = request.json.get('portion')

    if not isinstance(portion, int) or portion < 1:
        return make_json_response(False, "참여 수량은 1 이상이어야 합니다.")

    post = db.posts.find_one({"_id": ObjectId(post_id)})
    if not post:
        return make_json_response(False, "게시글이 존재하지 않습니다.")

    participants = post.get('participants', [])
    my_id = str(g.user['_id'])

    # 이미 참여한 사람인지 확인
    if any(str(p['user_id']) == my_id for p in participants):
        return make_json_response(False, "이미 참여하셨습니다.")

    used = sum(p.get('portion', 0) for p in participants)
    max_portion = post.get('max_portion', 1)

    if used + portion > max_portion:
        return make_json_response(False, f"총 인원({max_portion})을 초과할 수 없습니다.")

    # 예상 금액 계산 (올림 처리) db에 저장
    unit_price = math.ceil(post.get('total_price', 0) / max_portion)
    amount = unit_price * portion

    db.posts.update_one(
        {"_id": ObjectId(post_id)},
        {"$push": {
            "participants": {
                "user_id": ObjectId(g.user['_id']),
                "portion": portion,
                "amount": amount,
                "status": "대기"
            }
        }}
    )

    return make_json_response(True, "참여가 완료되었습니다.", {
        "portion": portion,
        "amount": amount
    })


   
#실시간 예상금액
@bp.route('/post/<post_id>/expected_price', methods=['GET'])
@login_required
def expected_price(post_id):
    db = get_db()
    portion_param = request.args.get('portion')

    try:
        portion = int(portion_param)
        if portion < 1:
            raise ValueError
    except (TypeError, ValueError):
        return make_json_response(False, "올바른 참여 수량을 입력해주세요.")

    post = db.posts.find_one({"_id": ObjectId(post_id)})
    if not post:
        return make_json_response(False, "게시글이 존재하지 않습니다.")

    max_portion = post.get('max_portion', 1)
    total_price = post.get('total_price', 0)

    if max_portion < 1:
        return make_json_response(False, "max_portion이 유효하지 않습니다.")

    # 올림 처리
    unit_price = math.ceil(total_price / max_portion)
    estimated_price = unit_price * portion

    return make_json_response(True, "예상 금액입니다.", {
        "unit_price": unit_price,
        "input_portion": portion,
        "estimated_price": estimated_price
    })