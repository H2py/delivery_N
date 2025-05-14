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
