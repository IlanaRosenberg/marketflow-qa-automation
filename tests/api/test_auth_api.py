"""
API tests for authentication endpoints.
Covers: register, login, logout, /me
"""
import pytest


pytestmark = [pytest.mark.api, pytest.mark.regression]


class TestRegister:
    @pytest.mark.sanity
    def test_register_success(self, client):
        res = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "Pass123!",
            "first_name": "New",
            "last_name": "User",
        })
        data = res.get_json()
        assert res.status_code == 201
        assert data["success"] is True
        assert data["data"]["username"] == "newuser"
        assert data["data"]["email"] == "new@example.com"
        assert "id" in data["data"]
        assert data["error"] is None

    def test_register_duplicate_username(self, client):
        res = client.post("/api/auth/register", json={
            "username": "testuser1",
            "email": "unique@example.com",
            "password": "Pass123!",
        })
        data = res.get_json()
        assert res.status_code == 400
        assert data["success"] is False
        assert "username" in data["error"].lower()

    def test_register_duplicate_email(self, client):
        res = client.post("/api/auth/register", json={
            "username": "uniqueuser",
            "email": "testuser1@example.com",
            "password": "Pass123!",
        })
        data = res.get_json()
        assert res.status_code == 400
        assert data["success"] is False
        assert "email" in data["error"].lower()

    def test_register_missing_username(self, client):
        res = client.post("/api/auth/register", json={
            "email": "a@b.com",
            "password": "Pass123!",
        })
        assert res.status_code == 400
        assert res.get_json()["success"] is False

    def test_register_invalid_email(self, client):
        res = client.post("/api/auth/register", json={
            "username": "someone",
            "email": "not-an-email",
            "password": "Pass123!",
        })
        assert res.status_code == 400
        assert res.get_json()["success"] is False

    def test_register_short_password(self, client):
        res = client.post("/api/auth/register", json={
            "username": "someone",
            "email": "someone@example.com",
            "password": "abc",
        })
        assert res.status_code == 400
        assert res.get_json()["success"] is False


class TestLogin:
    @pytest.mark.smoke
    @pytest.mark.sanity
    def test_login_success(self, client):
        res = client.post("/api/auth/login", json={
            "email": "testuser1@example.com",
            "password": "Password123!",
        })
        data = res.get_json()
        assert res.status_code == 200
        assert data["success"] is True
        assert "token" in data["data"]
        assert data["data"]["username"] == "testuser1"
        assert data["data"]["user_id"] is not None

    def test_login_wrong_password(self, client):
        res = client.post("/api/auth/login", json={
            "email": "testuser1@example.com",
            "password": "WrongPass!",
        })
        data = res.get_json()
        assert res.status_code == 401
        assert data["success"] is False
        assert data["data"] is None

    def test_login_nonexistent_user(self, client):
        res = client.post("/api/auth/login", json={
            "email": "ghost@example.com",
            "password": "Password123!",
        })
        assert res.status_code == 401
        assert res.get_json()["success"] is False

    def test_login_missing_email(self, client):
        res = client.post("/api/auth/login", json={"password": "Password123!"})
        assert res.status_code == 400
        assert res.get_json()["success"] is False

    def test_login_missing_password(self, client):
        res = client.post("/api/auth/login", json={"email": "testuser1@example.com"})
        assert res.status_code == 400
        assert res.get_json()["success"] is False


class TestLogout:
    def test_logout_success(self, client, auth_headers):
        res = client.post("/api/auth/logout", headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json()["success"] is True

    def test_logout_no_token(self, client):
        res = client.post("/api/auth/logout")
        assert res.status_code == 401
        assert res.get_json()["success"] is False

    def test_logout_invalid_token(self, client):
        res = client.post("/api/auth/logout", headers={"Authorization": "Bearer fake.token.here"})
        assert res.status_code == 401


class TestGetMe:
    @pytest.mark.smoke
    @pytest.mark.sanity
    def test_get_me_authenticated(self, client, auth_headers):
        res = client.get("/api/auth/me", headers=auth_headers)
        data = res.get_json()
        assert res.status_code == 200
        assert data["success"] is True
        assert data["data"]["username"] == "testuser1"
        assert data["data"]["email"] == "testuser1@example.com"

    def test_get_me_unauthenticated(self, client):
        res = client.get("/api/auth/me")
        assert res.status_code == 401
        assert res.get_json()["success"] is False
