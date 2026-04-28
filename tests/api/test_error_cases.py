"""
Edge case and error handling tests.
Validates consistent error response format and boundary conditions.
"""
import pytest
import jwt
import time

pytestmark = [pytest.mark.api, pytest.mark.regression]


class TestResponseFormat:
    def test_error_response_has_required_fields(self, client):
        """All error responses must have success=false, data=null, error=string."""
        res = client.post("/api/auth/login", json={"email": "bad@x.com", "password": "wrong"})
        data = res.get_json()
        assert "success" in data
        assert "data" in data
        assert "error" in data
        assert data["success"] is False
        assert data["data"] is None
        assert isinstance(data["error"], str)

    def test_success_response_has_required_fields(self, client):
        """All success responses must have success=true, data=object/null, error=null."""
        res = client.get("/api/products/")
        data = res.get_json()
        assert "success" in data
        assert "data" in data
        assert "error" in data
        assert data["success"] is True
        assert data["error"] is None


class TestMalformedRequests:
    def test_malformed_json_register(self, client):
        res = client.post(
            "/api/auth/register",
            data="not-json",
            content_type="application/json",
        )
        assert res.status_code == 400
        assert res.get_json()["success"] is False

    def test_malformed_json_login(self, client):
        res = client.post(
            "/api/auth/login",
            data="{broken json",
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_empty_body_add_to_cart(self, client, auth_headers):
        res = client.post("/api/cart/add", headers=auth_headers,
                          data=None, content_type="application/json")
        assert res.status_code == 400


class TestJWTEdgeCases:
    def test_expired_jwt_token(self, client, app):
        """An expired token must return 401."""
        with app.app_context():
            token = jwt.encode(
                {"user_id": 1, "exp": 1},  # exp in the past
                app.config["JWT_SECRET_KEY"],
                algorithm="HS256",
            )
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
        assert "expired" in res.get_json()["error"].lower()

    def test_invalid_jwt_signature(self, client):
        fake_token = jwt.encode(
            {"user_id": 1, "exp": int(time.time()) + 3600},
            "wrong-secret",
            algorithm="HS256",
        )
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {fake_token}"})
        assert res.status_code == 401

    def test_malformed_jwt_format(self, client):
        res = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
        assert res.status_code == 401

    def test_bearer_prefix_missing(self, client, jwt_token):
        res = client.get("/api/auth/me", headers={"Authorization": jwt_token})
        assert res.status_code == 401


class TestBoundaryConditions:
    def test_product_id_zero(self, client):
        res = client.get("/api/products/0")
        assert res.status_code == 404

    def test_order_id_zero(self, client, auth_headers):
        res = client.get("/api/orders/0", headers=auth_headers)
        assert res.status_code == 404

    def test_per_page_too_large(self, client):
        res = client.get("/api/products/?per_page=200")
        assert res.status_code == 400
