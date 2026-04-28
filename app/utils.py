import jwt
from datetime import datetime, timedelta, timezone
from flask import current_app


def encode_jwt(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc)
        + timedelta(hours=current_app.config["JWT_EXPIRATION_HOURS"]),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def decode_jwt(token: str) -> dict:
    return jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])


def success_response(data, status_code=200):
    from flask import jsonify
    return jsonify({"success": True, "data": data, "error": None}), status_code


def error_response(message: str, status_code=400):
    from flask import jsonify
    return jsonify({"success": False, "data": None, "error": message}), status_code
