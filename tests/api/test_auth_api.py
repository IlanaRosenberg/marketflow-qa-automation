"""
API tests for authentication endpoints.
Covers: register, login, logout, /me
"""
import pytest
import allure
from tests.conftest import attach_response

pytestmark = [pytest.mark.api, pytest.mark.regression]


@allure.feature("Authentication")
@allure.story("User Registration")
class TestRegister:
    @pytest.mark.sanity
    @allure.title("Register new user successfully")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_register_success(self, client):
        res = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "Pass123!",
            "first_name": "New",
            "last_name": "User",
        })
        attach_response(res, "Register response")
        data = res.get_json()
        assert res.status_code == 201
        assert data["success"] is True
        assert data["data"]["username"] == "newuser"
        assert data["data"]["email"] == "new@example.com"
        assert "id" in data["data"]
        assert data["error"] is None

    @allure.title("Register with duplicate username returns 400")
    @allure.severity(allure.severity_level.NORMAL)
    def test_register_duplicate_username(self, client):
        res = client.post("/api/auth/register", json={
            "username": "testuser1",
            "email": "unique@example.com",
            "password": "Pass123!",
        })
        attach_response(res, "Register duplicate username response")
        data = res.get_json()
        assert res.status_code == 400
        assert data["success"] is False
        assert "username" in data["error"].lower()

    @allure.title("Register with duplicate email returns 400")
    @allure.severity(allure.severity_level.NORMAL)
    def test_register_duplicate_email(self, client):
        res = client.post("/api/auth/register", json={
            "username": "uniqueuser",
            "email": "testuser1@example.com",
            "password": "Pass123!",
        })
        attach_response(res, "Register duplicate email response")
        data = res.get_json()
        assert res.status_code == 400
        assert data["success"] is False
        assert "email" in data["error"].lower()

    @allure.title("Register without username returns 400")
    @allure.severity(allure.severity_level.MINOR)
    def test_register_missing_username(self, client):
        res = client.post("/api/auth/register", json={
            "email": "a@b.com",
            "password": "Pass123!",
        })
        attach_response(res, "Register missing username response")
        assert res.status_code == 400
        assert res.get_json()["success"] is False

    @allure.title("Register with invalid email format returns 400")
    @allure.severity(allure.severity_level.MINOR)
    def test_register_invalid_email(self, client):
        res = client.post("/api/auth/register", json={
            "username": "someone",
            "email": "not-an-email",
            "password": "Pass123!",
        })
        attach_response(res, "Register invalid email response")
        assert res.status_code == 400
        assert res.get_json()["success"] is False

    @allure.title("Register with short password returns 400")
    @allure.severity(allure.severity_level.MINOR)
    def test_register_short_password(self, client):
        res = client.post("/api/auth/register", json={
            "username": "someone",
            "email": "someone@example.com",
            "password": "abc",
        })
        attach_response(res, "Register short password response")
        assert res.status_code == 400
        assert res.get_json()["success"] is False


@allure.feature("Authentication")
@allure.story("User Login")
class TestLogin:
    @pytest.mark.smoke
    @pytest.mark.sanity
    @allure.title("Login with valid credentials returns JWT token")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_login_success(self, client):
        res = client.post("/api/auth/login", json={
            "email": "testuser1@example.com",
            "password": "Password123!",
        })
        attach_response(res, "Login success response")
        data = res.get_json()
        assert res.status_code == 200
        assert data["success"] is True
        assert "token" in data["data"]
        assert data["data"]["username"] == "testuser1"
        assert data["data"]["user_id"] is not None

    @allure.title("Login with wrong password returns 401")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_wrong_password(self, client):
        res = client.post("/api/auth/login", json={
            "email": "testuser1@example.com",
            "password": "WrongPass!",
        })
        attach_response(res, "Login wrong password response")
        data = res.get_json()
        assert res.status_code == 401
        assert data["success"] is False
        assert data["data"] is None

    @allure.title("Login with non-existent user returns 401")
    @allure.severity(allure.severity_level.NORMAL)
    def test_login_nonexistent_user(self, client):
        res = client.post("/api/auth/login", json={
            "email": "ghost@example.com",
            "password": "Password123!",
        })
        attach_response(res, "Login nonexistent user response")
        assert res.status_code == 401
        assert res.get_json()["success"] is False

    @allure.title("Login without email field returns 400")
    @allure.severity(allure.severity_level.MINOR)
    def test_login_missing_email(self, client):
        res = client.post("/api/auth/login", json={"password": "Password123!"})
        attach_response(res, "Login missing email response")
        assert res.status_code == 400
        assert res.get_json()["success"] is False

    @allure.title("Login without password field returns 400")
    @allure.severity(allure.severity_level.MINOR)
    def test_login_missing_password(self, client):
        res = client.post("/api/auth/login", json={"email": "testuser1@example.com"})
        attach_response(res, "Login missing password response")
        assert res.status_code == 400
        assert res.get_json()["success"] is False


@allure.feature("Authentication")
@allure.story("Logout")
class TestLogout:
    @allure.title("Logout with valid token returns 200")
    @allure.severity(allure.severity_level.NORMAL)
    def test_logout_success(self, client, auth_headers):
        res = client.post("/api/auth/logout", headers=auth_headers)
        attach_response(res, "Logout response")
        assert res.status_code == 200
        assert res.get_json()["success"] is True

    @allure.title("Logout without token returns 401")
    @allure.severity(allure.severity_level.NORMAL)
    def test_logout_no_token(self, client):
        res = client.post("/api/auth/logout")
        attach_response(res, "Logout no token response")
        assert res.status_code == 401
        assert res.get_json()["success"] is False

    @allure.title("Logout with invalid token returns 401")
    @allure.severity(allure.severity_level.MINOR)
    def test_logout_invalid_token(self, client):
        res = client.post("/api/auth/logout",
                          headers={"Authorization": "Bearer fake.token.here"})
        attach_response(res, "Logout invalid token response")
        assert res.status_code == 401


@allure.feature("Authentication")
@allure.story("Current User Profile")
class TestGetMe:
    @pytest.mark.smoke
    @pytest.mark.sanity
    @allure.title("GET /me returns authenticated user profile")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_me_authenticated(self, client, auth_headers):
        res = client.get("/api/auth/me", headers=auth_headers)
        attach_response(res, "GET /me response")
        data = res.get_json()
        assert res.status_code == 200
        assert data["success"] is True
        assert data["data"]["username"] == "testuser1"
        assert data["data"]["email"] == "testuser1@example.com"

    @allure.title("GET /me without token returns 401")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_me_unauthenticated(self, client):
        res = client.get("/api/auth/me")
        attach_response(res, "GET /me unauthenticated response")
        assert res.status_code == 401
        assert res.get_json()["success"] is False
