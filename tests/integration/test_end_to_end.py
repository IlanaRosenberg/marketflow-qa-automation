"""
End-to-end integration tests.
Full user journeys: register → login → browse → cart → checkout → order history.
These tests exercise the entire stack through the API client.
"""
import pytest
import allure

pytestmark = [pytest.mark.integration, pytest.mark.sanity, pytest.mark.regression]

IN_STOCK_ID = 1    # Laptop Pro: $1299.99, stock=10
MOUSE_ID = 2       # Wireless Mouse: $29.99, stock=50
BOOK_ID = 9        # Book: $14.99, stock=100


@allure.feature("End-to-End Flows")
@allure.story("Full User Journey")
class TestFullUserJourney:
    @allure.title("Full journey: register → login → browse → cart → checkout → history")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_register_login_browse_cart_checkout(self, client):
        """Full happy path: new user → register → login → add to cart → checkout → view order."""
        # Step 1: Register
        reg = client.post("/api/auth/register", json={
            "username": "e2euser",
            "email": "e2e@test.com",
            "password": "E2EPass123!",
        })
        assert reg.status_code == 201

        # Step 2: Login
        login = client.post("/api/auth/login", json={
            "email": "e2e@test.com",
            "password": "E2EPass123!",
        })
        assert login.status_code == 200
        token = login.get_json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 3: Browse products
        products = client.get("/api/products/")
        assert products.status_code == 200
        assert products.get_json()["data"]["total"] == 20  # 20 seeded products

        # Step 4: View product detail
        detail = client.get(f"/api/products/{BOOK_ID}")
        assert detail.status_code == 200
        assert detail.get_json()["data"]["name"] == "The QA Engineer Handbook"

        # Step 5: Add to cart
        add = client.post("/api/cart/add", headers=headers,
                          json={"product_id": BOOK_ID, "quantity": 2})
        assert add.status_code == 200
        assert add.get_json()["data"]["item_count"] == 1

        # Step 6: Verify cart
        cart = client.get("/api/cart/", headers=headers)
        assert cart.get_json()["data"]["total_price"] == round(14.99 * 2, 2)

        # Step 7: Checkout
        order = client.post("/api/orders/checkout", headers=headers,
                            json={"payment_method": "credit_card"})
        assert order.status_code == 201
        order_data = order.get_json()["data"]
        assert order_data["status"] == "completed"
        assert order_data["total_price"] == round(14.99 * 2, 2)
        order_id = order_data["id"]

        # Step 8: Cart is empty
        cart_after = client.get("/api/cart/", headers=headers)
        assert cart_after.get_json()["data"]["item_count"] == 0

        # Step 9: Order in history
        history = client.get("/api/orders/", headers=headers)
        assert history.get_json()["data"]["total"] == 1

        # Step 10: View order detail
        order_detail = client.get(f"/api/orders/{order_id}", headers=headers)
        assert order_detail.status_code == 200
        assert order_detail.get_json()["data"]["id"] == order_id

    def test_multi_product_order_journey(self, client, auth_headers):
        """Add 3 different products, checkout, verify all items in order."""
        products_to_add = [(IN_STOCK_ID, 1), (MOUSE_ID, 3), (BOOK_ID, 5)]
        for pid, qty in products_to_add:
            res = client.post("/api/cart/add", headers=auth_headers,
                              json={"product_id": pid, "quantity": qty})
            assert res.status_code == 200

        # Verify cart before checkout
        cart = client.get("/api/cart/", headers=auth_headers).get_json()["data"]
        assert cart["item_count"] == 3
        expected_total = round(1299.99 * 1 + 29.99 * 3 + 14.99 * 5, 2)
        assert cart["total_price"] == expected_total

        # Checkout
        order = client.post("/api/orders/checkout", headers=auth_headers,
                            json={"payment_method": "credit_card"})
        assert order.status_code == 201
        order_data = order.get_json()["data"]
        assert len(order_data["items"]) == 3
        assert order_data["total_price"] == expected_total

    def test_guest_cannot_access_protected_resources(self, client):
        """Unauthenticated user is blocked from cart and orders."""
        assert client.get("/api/cart/").status_code == 401
        assert client.post("/api/orders/checkout").status_code == 401
        assert client.get("/api/orders/").status_code == 401

    def test_search_and_add_to_order_flow(self, client, auth_headers):
        """Search for a product by name, add it, and checkout."""
        search = client.get("/api/products/?search=Yoga")
        products = search.get_json()["data"]["products"]
        assert len(products) == 1
        yoga_id = products[0]["id"]

        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": yoga_id, "quantity": 1})
        order = client.post("/api/orders/checkout", headers=auth_headers,
                            json={"payment_method": "credit_card"})
        assert order.status_code == 201
        assert order.get_json()["data"]["status"] == "completed"

    def test_order_cancel_flow(self, client, auth_headers):
        """Create order, manually set to pending, cancel it, verify status."""
        from app.models import Order
        from app.database import db

        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": MOUSE_ID, "quantity": 1})
        order_res = client.post("/api/orders/checkout", headers=auth_headers,
                                json={"payment_method": "credit_card"})
        order_id = order_res.get_json()["data"]["id"]

        with client.application.app_context():
            order = Order.query.get(order_id)
            order.status = "pending"
            db.session.commit()

        cancel = client.post(f"/api/orders/{order_id}/cancel", headers=auth_headers)
        assert cancel.status_code == 200
        assert cancel.get_json()["data"]["status"] == "cancelled"

        detail = client.get(f"/api/orders/{order_id}", headers=auth_headers)
        assert detail.get_json()["data"]["status"] == "cancelled"
