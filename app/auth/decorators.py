import jwt
from functools import wraps
from flask import request, g
from app.utils import error_response
from app.models import User


def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

        if not token:
            return error_response("Authorization token is missing", 401)

        try:
            from flask import current_app
            import jwt as pyjwt
            payload = pyjwt.decode(
                token,
                current_app.config["JWT_SECRET_KEY"],
                algorithms=["HS256"],
            )
            g.current_user = User.query.get(payload["user_id"])
            if not g.current_user:
                return error_response("User not found", 401)
        except pyjwt.ExpiredSignatureError:
            return error_response("Token has expired", 401)
        except pyjwt.InvalidTokenError:
            return error_response("Invalid token", 401)

        return f(*args, **kwargs)

    return decorated
