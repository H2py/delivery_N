from flask import jsonify

def make_response(success, message, result=None):
    if result is None:
        result = []
    return jsonify({
        "success": success,
        "message": message,
        "result": result
    })