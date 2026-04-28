from flask import Blueprint, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.database import db
from app.models import User
from app.utils import encode_jwt, success_response, error_response
from app.auth.decorators import jwt_required
from flask import g

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username, email, password]
          properties:
            username:
              type: string
              example: testuser1
            email:
              type: string
              example: testuser1@example.com
            password:
              type: string
              example: Password123!
            first_name:
              type: string
            last_name:
              type: string
    responses:
      201:
        description: User registered successfully
      400:
        description: Validation error or duplicate user
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("Request body must be valid JSON", 400)

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not username:
        return error_response("Username is required", 400)
    if not email or "@" not in email:
        return error_response("Valid email is required", 400)
    if not password or len(password) < 6:
        return error_response("Password must be at least 6 characters", 400)

    if User.query.filter_by(username=username).first():
        return error_response("Username already exists", 400)
    if User.query.filter_by(email=email).first():
        return error_response("Email already registered", 400)

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        first_name=(data.get("first_name") or "").strip() or None,
        last_name=(data.get("last_name") or "").strip() or None,
    )
    db.session.add(user)
    db.session.commit()

    return success_response({"id": user.id, "username": user.username, "email": user.email}, 201)


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login and receive a JWT token
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email, password]
          properties:
            email:
              type: string
              example: testuser1@example.com
            password:
              type: string
              example: Password123!
    responses:
      200:
        description: Login successful, returns JWT token
      400:
        description: Missing fields
      401:
        description: Invalid credentials
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("Request body must be valid JSON", 400)

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email:
        return error_response("Email is required", 400)
    if not password:
        return error_response("Password is required", 400)

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return error_response("Invalid email or password", 401)

    token = encode_jwt(user.id)
    session["user_id"] = user.id

    return success_response({
        "token": token,
        "user_id": user.id,
        "username": user.username,
    })


@auth_bp.route("/logout", methods=["POST"])
@jwt_required
def logout():
    """
    Logout the current user
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    responses:
      200:
        description: Logged out successfully
      401:
        description: Unauthorized
    """
    session.pop("user_id", None)
    return success_response(None)


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def me():
    """
    Get current authenticated user details
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    responses:
      200:
        description: Current user data
      401:
        description: Unauthorized
    """
    return success_response(g.current_user.to_dict())
