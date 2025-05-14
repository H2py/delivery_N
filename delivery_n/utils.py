from datetime import datetime, timedelta, timezone
from flask import jsonify, request
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, set_access_cookies

def make_json_response(success, message, result=None):
    if result is None:
        result = []
    return jsonify({
        "success": success,
        "message": message,
        "result": result
    })
    

    # Using an `after_request` callback, we refresh any token that is within 30
    # minutes of expiring. Change the timedeltas to match the needs of your application.
def refresh_expiring_jwts(response):
    try:
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            set_access_cookies(response, access_token)
        return response
    except (RuntimeError, KeyError):
        return response
    
    
def get_next_sequence(db, name):
    # name을 기반으로 컬렉션 결정 (예: 'post_id'면 'posts' 컬렉션 사용)
    if name == 'post_id':
        collection_name = 'posts'
    else:
        collection_name = name
    
    # 해당 컬렉션에서 가장 큰 number 값 찾기
    result = db[collection_name].find_one(
        {},
        sort=[("number", -1)]  # number 필드 기준 내림차순 정렬
    )
    
    # 결과가 있으면 number + 1 반환, 없으면 1 반환
    if result and 'number' in result:
        return result['number'] + 1
    else:
        return 1