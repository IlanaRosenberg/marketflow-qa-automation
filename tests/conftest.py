import pytest
from app import create_app
from app.database import db as _db
from seed_data.seed import seed_db


@pytest.fixture(scope="function")
def app():
    """Create a fresh Flask app with in-memory DB for each test."""
    flask_app = create_app("testing")
    with flask_app.app_context():
        _db.create_all()
        seed_db()
        yield flask_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function")
def jwt_token(client):
    """Return a valid JWT token for testuser1."""
    res = client.post(
        "/api/auth/login",
        json={"email": "testuser1@example.com", "password": "Password123!"},
    )
    return res.get_json()["data"]["token"]


@pytest.fixture(scope="function")
def jwt_token_user2(client):
    """Return a valid JWT token for testuser2."""
    res = client.post(
        "/api/auth/login",
        json={"email": "testuser2@example.com", "password": "Password123!"},
    )
    return res.get_json()["data"]["token"]


@pytest.fixture(scope="function")
def auth_headers(jwt_token):
    return {"Authorization": f"Bearer {jwt_token}"}


@pytest.fixture(scope="function")
def auth_headers_user2(jwt_token_user2):
    return {"Authorization": f"Bearer {jwt_token_user2}"}
