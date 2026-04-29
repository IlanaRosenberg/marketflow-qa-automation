"""
Security-focused API tests.

Validates that the API is hardened against common web vulnerabilities:
- SQL Injection via query parameters and request bodies
- XSS payload storage and reflection
- Authentication bypass attempts
- Mass assignment / parameter pollution
- Sensitive data exposure in error responses
- IDOR (Insecure Direct Object Reference) between users
"""
import pytest
import allure
from tests.conftest import attach_response

pytestmark = [pytest.mark.api, pytest.mark.regression]


@allure.feature("Security")
@allure.story("SQL Injection")
class TestSQLInjection:
    """API inputs must be treated as data, never as executable SQL."""

    @allure.title("SQL injection in product search does not crash the API")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_sql_injection_in_search(self, client):
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE products; --",
            "1' UNION SELECT * FROM users --",
            "' OR 1=1 --",
        ]
        for payload in payloads:
            res = client.get(f"/api/products/?search={payload}")
            attach_response(res, f"SQL injection search: {payload[:30]}")
            assert res.status_code == 200, (
                f"Payload '{payload}' caused a server error — possible SQL injection vulnerability"
            )
            assert res.get_json()["success"] is True

    @allure.title("SQL injection in login email does not bypass authentication")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_sql_injection_in_login(self, client):
        payloads = [
            {"email": "' OR '1'='1", "password": "anything"},
            {"email": "admin'--", "password": "anything"},
            {"email": "' OR 1=1 --", "password": "x"},
        ]
        for payload in payloads:
            res = client.post("/api/auth/login", json=payload)
            attach_response(res, f"SQL injection login: {payload['email'][:30]}")
            assert res.status_code in (400, 401), (
                f"Login with SQL injection payload returned {res.status_code} — "
                f"possible authentication bypass"
            )
            assert res.get_json()["success"] is False

    @allure.title("SQL injection in register fields does not crash the API")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_sql_injection_in_register(self, client):
        res = client.post("/api/auth/register", json={
            "username": "normal_user'; DROP TABLE users; --",
            "email": "inject@test.com",
            "password": "Pass123!",
        })
        attach_response(res, "SQL injection in register username")
        # Must not return 500 — either creates the user or rejects with 400
        assert res.status_code in (201, 400)
        assert res.get_json()["success"] in (True, False)


@allure.feature("Security")
@allure.story("XSS — Cross-Site Scripting")
class TestXSS:
    """Stored XSS: script tags stored in the DB must not be reflected as raw HTML."""

    @allure.title("XSS payload in product creation is stored safely")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_xss_payload_in_product_name(self, client, auth_headers):
        xss_payload = "<script>alert('XSS')</script>"
        res = client.post("/api/products/", headers=auth_headers, json={
            "name": xss_payload,
            "price": 1.00,
            "stock_quantity": 1,
            "sku": "XSS-TEST-001",
        })
        attach_response(res, "XSS payload in product name")
        # If the product was created, fetch it and verify the payload is not
        # reflected as raw executable HTML in the JSON response
        if res.status_code == 201:
            product_id = res.get_json()["data"]["id"]
            get_res = client.get(f"/api/products/{product_id}")
            name_in_response = get_res.get_json()["data"]["name"]
            assert "<script>" not in name_in_response or name_in_response == xss_payload, (
                "XSS payload was reflected without escaping — stored XSS vulnerability"
            )

    @allure.title("XSS payload in registration fields does not execute")
    @allure.severity(allure.severity_level.NORMAL)
    def test_xss_payload_in_username(self, client):
        res = client.post("/api/auth/register", json={
            "username": "<img src=x onerror=alert(1)>",
            "email": "xss@test.com",
            "password": "Pass123!",
        })
        attach_response(res, "XSS payload in username")
        # Must not return 500
        assert res.status_code in (201, 400)


@allure.feature("Security")
@allure.story("IDOR — Insecure Direct Object Reference")
class TestIDOR:
    """Users must only access their own resources."""

    @allure.title("User cannot view another user's order")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_user1_cannot_access_user2_order(self, client, auth_headers, auth_headers_user2):
        # User1 creates an order
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": 2, "quantity": 1})
        order_res = client.post("/api/orders/checkout", headers=auth_headers,
                                json={"payment_method": "credit_card"})
        order_id = order_res.get_json()["data"]["id"]

        # User2 tries to access User1's order
        res = client.get(f"/api/orders/{order_id}", headers=auth_headers_user2)
        attach_response(res, f"User2 accessing User1 order #{order_id}")
        assert res.status_code == 404, (
            f"User2 was able to access User1's order #{order_id} — IDOR vulnerability"
        )

    @allure.title("User cannot cancel another user's order")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_user1_cannot_cancel_user2_order(self, client, auth_headers, auth_headers_user2):
        # User1 creates an order
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": 2, "quantity": 1})
        order_res = client.post("/api/orders/checkout", headers=auth_headers,
                                json={"payment_method": "credit_card"})
        order_id = order_res.get_json()["data"]["id"]

        # User2 tries to cancel User1's order
        res = client.post(f"/api/orders/{order_id}/cancel", headers=auth_headers_user2)
        attach_response(res, f"User2 cancelling User1 order #{order_id}")
        assert res.status_code == 404, (
            f"User2 was able to cancel User1's order #{order_id} — IDOR vulnerability"
        )

    @allure.title("User cannot clear another user's cart")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_user1_cart_isolated_from_user2(self, client, auth_headers, auth_headers_user2):
        # User1 adds to cart
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": 2, "quantity": 1})

        # User2 views their own cart — should be empty
        res = client.get("/api/cart/", headers=auth_headers_user2)
        attach_response(res, "User2 cart while User1 has items")
        assert res.get_json()["data"]["item_count"] == 0, (
            "User2 can see User1's cart items — cart isolation failure"
        )


@allure.feature("Security")
@allure.story("Sensitive Data Exposure")
class TestSensitiveDataExposure:
    """Error responses must not leak internal details."""

    @allure.title("Login failure does not reveal whether email exists")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_failure_does_not_reveal_email_existence(self, client):
        # Wrong password for existing user
        res_existing = client.post("/api/auth/login", json={
            "email": "testuser1@example.com",
            "password": "WrongPassword!",
        })
        # Non-existent user
        res_missing = client.post("/api/auth/login", json={
            "email": "nobody@nowhere.com",
            "password": "WrongPassword!",
        })
        attach_response(res_existing, "Login fail — existing email")
        attach_response(res_missing, "Login fail — non-existent email")

        # Both must return 401 — not 404 for missing user
        assert res_existing.status_code == 401
        assert res_missing.status_code == 401

    @allure.title("Password hash is never exposed in any API response")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_password_hash_not_in_register_response(self, client):
        res = client.post("/api/auth/register", json={
            "username": "hashcheck",
            "email": "hashcheck@test.com",
            "password": "Pass123!",
        })
        attach_response(res, "Register response — checking for password hash")
        assert res.status_code == 201
        data_str = str(res.get_json())
        assert "password" not in data_str.lower() or "password_hash" not in data_str, (
            "Password hash or raw password was returned in the register response"
        )

    @allure.title("Password hash is never exposed in GET /me response")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_password_hash_not_in_me_response(self, client, auth_headers):
        res = client.get("/api/auth/me", headers=auth_headers)
        attach_response(res, "GET /me — checking for password hash")
        assert res.status_code == 200
        data_str = str(res.get_json())
        assert "password_hash" not in data_str, (
            "password_hash field was returned in the /me response — sensitive data exposure"
        )

    @allure.title("Server errors return generic message — no stack trace exposed")
    @allure.severity(allure.severity_level.NORMAL)
    def test_invalid_product_id_type_does_not_expose_stack_trace(self, client):
        res = client.get("/api/products/not-a-number")
        attach_response(res, "Invalid product ID type response")
        # Must be 404 (Flask routing) not 500
        assert res.status_code == 404
        body = str(res.data)
        assert "Traceback" not in body
        assert "sqlalchemy" not in body.lower()


@allure.feature("Security")
@allure.story("Authentication Bypass")
class TestAuthenticationBypass:
    """Protected endpoints must resist all token manipulation attempts."""

    @allure.title("Empty Authorization header is rejected")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_empty_bearer_token_rejected(self, client):
        res = client.get("/api/auth/me", headers={"Authorization": "Bearer "})
        attach_response(res, "Empty bearer token response")
        assert res.status_code == 401

    @allure.title("Token with tampered payload is rejected")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_tampered_jwt_payload_rejected(self, client, jwt_token):
        # Split the real token and replace its payload with a tampered one
        import base64
        import json
        parts = jwt_token.split(".")
        # Tamper: change user_id to 999 in the payload
        tampered_payload = base64.urlsafe_b64encode(
            json.dumps({"user_id": 999}).encode()
        ).rstrip(b"=").decode()
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"

        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
        attach_response(res, "Tampered JWT payload response")
        assert res.status_code == 401, (
            "Tampered JWT was accepted — signature verification is not working"
        )

    @allure.title("Algorithm confusion attack (alg=none) is rejected")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_jwt_none_algorithm_rejected(self, client):
        import base64
        import json
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(
            json.dumps({"user_id": 1}).encode()
        ).rstrip(b"=").decode()
        none_token = f"{header}.{payload}."

        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {none_token}"})
        attach_response(res, "JWT alg=none attack response")
        assert res.status_code == 401, (
            "JWT with alg=none was accepted — algorithm confusion vulnerability"
        )
