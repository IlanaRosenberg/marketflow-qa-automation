"""
API tests for order endpoints.
Bug-catching focus: stock decremented after checkout, cart cleared, cancel validation.
"""
import pytest

pytestmark = [pytest.mark.api, pytest.mark.regression]

IN_STOCK_ID = 1      # Laptop Pro: $1299.99, stock=10
MOUSE_ID = 2         # Wireless Mouse: $29.99, stock=50
OUT_OF_STOCK_ID = 3  # USB-C Cable: stock=0
LOW_STOCK_ID = 8     # Coffee Maker: stock=1


def _add_to_cart(client, headers, product_id, quantity=1):
    return client.post("/api/cart/add", headers=headers,
                       json={"product_id": product_id, "quantity": quantity})


def _checkout(client, headers, payment_method="credit_card"):
    return client.post("/api/orders/checkout", headers=headers,
                       json={"payment_method": payment_method})


class TestCheckout:
    @pytest.mark.smoke
    @pytest.mark.sanity
    def test_checkout_success(self, client, auth_headers):
        _add_to_cart(client, auth_headers, IN_STOCK_ID, 1)
        res = _checkout(client, auth_headers)
        data = res.get_json()
        assert res.status_code == 201
        assert data["success"] is True
        assert data["data"]["status"] == "completed"
        assert data["data"]["total_price"] == 1299.99
        assert "items" in data["data"]
        assert len(data["data"]["items"]) == 1

    def test_checkout_cart_cleared_after_order(self, client, auth_headers):
        """Bug-catcher: cart must be empty after successful checkout."""
        _add_to_cart(client, auth_headers, IN_STOCK_ID, 1)
        _checkout(client, auth_headers)
        cart_res = client.get("/api/cart/", headers=auth_headers)
        assert cart_res.get_json()["data"]["item_count"] == 0
        assert cart_res.get_json()["data"]["items"] == []

    def test_checkout_stock_decremented_after_order(self, client, auth_headers):
        """Bug-catcher: product stock must decrease by ordered quantity."""
        # Get initial stock
        before = client.get(f"/api/products/{IN_STOCK_ID}").get_json()["data"]["stock_quantity"]
        _add_to_cart(client, auth_headers, IN_STOCK_ID, 2)
        _checkout(client, auth_headers)
        after = client.get(f"/api/products/{IN_STOCK_ID}").get_json()["data"]["stock_quantity"]
        assert after == before - 2

    def test_checkout_order_total_matches_cart_total(self, client, auth_headers):
        """Bug-catcher: order total must equal cart total."""
        _add_to_cart(client, auth_headers, IN_STOCK_ID, 1)
        _add_to_cart(client, auth_headers, MOUSE_ID, 3)
        cart = client.get("/api/cart/", headers=auth_headers).get_json()["data"]
        cart_total = cart["total_price"]

        order_res = _checkout(client, auth_headers)
        order_total = order_res.get_json()["data"]["total_price"]
        assert order_total == cart_total

    def test_checkout_empty_cart_fails(self, client, auth_headers):
        res = _checkout(client, auth_headers)
        data = res.get_json()
        assert res.status_code == 400
        assert data["success"] is False
        assert "empty" in data["error"].lower()

    def test_checkout_unauthenticated(self, client):
        res = client.post("/api/orders/checkout", json={"payment_method": "credit_card"})
        assert res.status_code == 401

    def test_checkout_multi_product_items_recorded(self, client, auth_headers):
        _add_to_cart(client, auth_headers, IN_STOCK_ID, 1)
        _add_to_cart(client, auth_headers, MOUSE_ID, 2)
        res = _checkout(client, auth_headers)
        data = res.get_json()["data"]
        assert len(data["items"]) == 2
        product_ids = [i["product_id"] for i in data["items"]]
        assert IN_STOCK_ID in product_ids
        assert MOUSE_ID in product_ids


class TestListOrders:
    def test_list_orders_empty(self, client, auth_headers):
        res = client.get("/api/orders/", headers=auth_headers)
        data = res.get_json()
        assert res.status_code == 200
        assert data["success"] is True
        assert data["data"]["orders"] == []
        assert data["data"]["total"] == 0

    def test_list_orders_after_checkout(self, client, auth_headers):
        _add_to_cart(client, auth_headers, MOUSE_ID, 1)
        _checkout(client, auth_headers)
        res = client.get("/api/orders/", headers=auth_headers)
        data = res.get_json()
        assert data["data"]["total"] == 1
        assert len(data["data"]["orders"]) == 1

    def test_list_orders_status_filter(self, client, auth_headers):
        _add_to_cart(client, auth_headers, MOUSE_ID, 1)
        _checkout(client, auth_headers)
        res = client.get("/api/orders/?status=completed", headers=auth_headers)
        assert res.status_code == 200
        for order in res.get_json()["data"]["orders"]:
            assert order["status"] == "completed"

    def test_list_orders_invalid_status(self, client, auth_headers):
        res = client.get("/api/orders/?status=invalid", headers=auth_headers)
        assert res.status_code == 400

    def test_list_orders_unauthenticated(self, client):
        res = client.get("/api/orders/")
        assert res.status_code == 401

    def test_list_orders_only_own_orders(self, client, auth_headers, auth_headers_user2):
        """Bug-catcher: users must only see their own orders."""
        _add_to_cart(client, auth_headers, MOUSE_ID, 1)
        _checkout(client, auth_headers)
        res = client.get("/api/orders/", headers=auth_headers_user2)
        assert res.get_json()["data"]["total"] == 0


class TestGetOrderDetail:
    def test_get_order_detail_success(self, client, auth_headers):
        _add_to_cart(client, auth_headers, IN_STOCK_ID, 1)
        order_id = _checkout(client, auth_headers).get_json()["data"]["id"]
        res = client.get(f"/api/orders/{order_id}", headers=auth_headers)
        data = res.get_json()
        assert res.status_code == 200
        assert data["data"]["id"] == order_id
        assert "items" in data["data"]

    def test_get_order_detail_not_found(self, client, auth_headers):
        res = client.get("/api/orders/99999", headers=auth_headers)
        assert res.status_code == 404
        assert res.get_json()["success"] is False

    def test_get_order_detail_not_owned_by_user(self, client, auth_headers, auth_headers_user2):
        """Bug-catcher: user2 must not see user1's order."""
        _add_to_cart(client, auth_headers, MOUSE_ID, 1)
        order_id = _checkout(client, auth_headers).get_json()["data"]["id"]
        res = client.get(f"/api/orders/{order_id}", headers=auth_headers_user2)
        assert res.status_code == 404

    def test_get_order_detail_unauthenticated(self, client, auth_headers):
        _add_to_cart(client, auth_headers, MOUSE_ID, 1)
        order_id = _checkout(client, auth_headers).get_json()["data"]["id"]
        res = client.get(f"/api/orders/{order_id}")
        assert res.status_code == 401


class TestCancelOrder:
    def _create_pending_order(self, client, headers):
        """Helper: create a pending order directly in the DB via app context."""
        from app.models import Order
        from app.database import db
        # Since checkout creates "completed", we manually create a pending order
        _add_to_cart(client, headers, MOUSE_ID, 1)
        order_res = _checkout(client, headers)
        order_id = order_res.get_json()["data"]["id"]
        # Manually set to pending for cancel tests
        with client.application.app_context():
            order = Order.query.get(order_id)
            order.status = "pending"
            db.session.commit()
        return order_id

    def test_cancel_pending_order_success(self, client, auth_headers):
        order_id = self._create_pending_order(client, auth_headers)
        res = client.post(f"/api/orders/{order_id}/cancel", headers=auth_headers)
        data = res.get_json()
        assert res.status_code == 200
        assert data["success"] is True
        assert data["data"]["status"] == "cancelled"

    def test_cancelled_order_status_persists(self, client, auth_headers):
        """Bug-catcher: GET order after cancel must show 'cancelled'."""
        order_id = self._create_pending_order(client, auth_headers)
        client.post(f"/api/orders/{order_id}/cancel", headers=auth_headers)
        res = client.get(f"/api/orders/{order_id}", headers=auth_headers)
        assert res.get_json()["data"]["status"] == "cancelled"

    def test_cancel_completed_order_success(self, client, auth_headers):
        """Completed orders can be cancelled — status updates to 'cancelled'."""
        _add_to_cart(client, auth_headers, MOUSE_ID, 1)
        order_id = _checkout(client, auth_headers).get_json()["data"]["id"]
        res = client.post(f"/api/orders/{order_id}/cancel", headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json()["success"] is True
        assert res.get_json()["data"]["status"] == "cancelled"

    def test_cannot_cancel_already_cancelled_order(self, client, auth_headers):
        """Bug-catcher: second cancel must fail, not succeed silently."""
        order_id = self._create_pending_order(client, auth_headers)
        client.post(f"/api/orders/{order_id}/cancel", headers=auth_headers)
        res = client.post(f"/api/orders/{order_id}/cancel", headers=auth_headers)
        assert res.status_code == 400
        assert res.get_json()["success"] is False

    def test_cancel_order_not_found(self, client, auth_headers):
        res = client.post("/api/orders/99999/cancel", headers=auth_headers)
        assert res.status_code == 404

    def test_cancel_order_unauthenticated(self, client):
        res = client.post("/api/orders/1/cancel")
        assert res.status_code == 401
