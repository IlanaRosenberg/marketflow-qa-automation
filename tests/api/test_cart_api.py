"""
API tests for cart endpoints.
Bug-catching focus: exact count/total assertions, stock validation, deduplication.
"""
import pytest

pytestmark = [pytest.mark.api, pytest.mark.regression]

IN_STOCK_ID = 1      # Laptop Pro: $1299.99, stock=10
MOUSE_ID = 2         # Wireless Mouse: $29.99, stock=50
OUT_OF_STOCK_ID = 3  # USB-C Cable: stock=0
LOW_STOCK_ID = 8     # Coffee Maker: stock=1


class TestGetCart:
    @pytest.mark.smoke
    @pytest.mark.sanity
    def test_get_empty_cart(self, client, auth_headers):
        res = client.get("/api/cart/", headers=auth_headers)
        data = res.get_json()
        assert res.status_code == 200
        assert data["success"] is True
        assert data["data"]["items"] == []
        assert data["data"]["total_price"] == 0.0
        assert data["data"]["item_count"] == 0

    def test_get_cart_unauthenticated(self, client):
        res = client.get("/api/cart/")
        assert res.status_code == 401


class TestAddToCart:
    @pytest.mark.smoke
    @pytest.mark.sanity
    def test_add_to_cart_success(self, client, auth_headers):
        res = client.post("/api/cart/add", headers=auth_headers,
                          json={"product_id": IN_STOCK_ID, "quantity": 2})
        data = res.get_json()
        assert res.status_code == 200
        assert data["success"] is True
        assert data["data"]["item_count"] == 1
        assert data["data"]["total_price"] == round(1299.99 * 2, 2)
        # Verify exact item in cart
        items = data["data"]["items"]
        assert len(items) == 1
        assert items[0]["product_id"] == IN_STOCK_ID
        assert items[0]["quantity"] == 2

    def test_add_to_cart_out_of_stock_does_not_change_cart(self, client, auth_headers):
        """Bug-catcher: cart must remain empty after a failed add."""
        res = client.post("/api/cart/add", headers=auth_headers,
                          json={"product_id": OUT_OF_STOCK_ID, "quantity": 1})
        data = res.get_json()
        assert res.status_code == 409
        assert data["success"] is False

        # Verify cart is still empty
        cart_res = client.get("/api/cart/", headers=auth_headers)
        assert cart_res.get_json()["data"]["item_count"] == 0

    def test_add_to_cart_quantity_exceeds_stock(self, client, auth_headers):
        res = client.post("/api/cart/add", headers=auth_headers,
                          json={"product_id": LOW_STOCK_ID, "quantity": 5})
        assert res.status_code == 409
        assert res.get_json()["success"] is False

    def test_add_to_cart_invalid_product(self, client, auth_headers):
        res = client.post("/api/cart/add", headers=auth_headers,
                          json={"product_id": 99999, "quantity": 1})
        assert res.status_code == 404
        assert res.get_json()["success"] is False

    def test_add_to_cart_zero_quantity(self, client, auth_headers):
        res = client.post("/api/cart/add", headers=auth_headers,
                          json={"product_id": IN_STOCK_ID, "quantity": 0})
        assert res.status_code == 400
        assert res.get_json()["success"] is False

    def test_add_to_cart_negative_quantity(self, client, auth_headers):
        res = client.post("/api/cart/add", headers=auth_headers,
                          json={"product_id": IN_STOCK_ID, "quantity": -1})
        assert res.status_code == 400

    def test_add_to_cart_unauthenticated(self, client):
        res = client.post("/api/cart/add", json={"product_id": IN_STOCK_ID, "quantity": 1})
        assert res.status_code == 401

    def test_add_same_product_twice_increases_quantity_not_rows(self, client, auth_headers):
        """Bug-catcher: adding same product twice should merge, not create duplicate rows."""
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": MOUSE_ID, "quantity": 2})
        res = client.post("/api/cart/add", headers=auth_headers,
                          json={"product_id": MOUSE_ID, "quantity": 3})
        data = res.get_json()
        assert data["success"] is True
        assert data["data"]["item_count"] == 1  # Still one row
        assert data["data"]["items"][0]["quantity"] == 5  # 2 + 3

    def test_add_multiple_products_correct_total(self, client, auth_headers):
        """Bug-catcher: total must equal sum of all items."""
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": IN_STOCK_ID, "quantity": 1})
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": MOUSE_ID, "quantity": 2})
        res = client.get("/api/cart/", headers=auth_headers)
        data = res.get_json()["data"]
        expected_total = round(1299.99 * 1 + 29.99 * 2, 2)
        assert data["total_price"] == expected_total
        assert data["item_count"] == 2


class TestUpdateCartItem:
    def test_update_quantity_success(self, client, auth_headers):
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": IN_STOCK_ID, "quantity": 1})
        res = client.patch(f"/api/cart/item/{IN_STOCK_ID}", headers=auth_headers,
                           json={"quantity": 3})
        data = res.get_json()
        assert res.status_code == 200
        assert data["success"] is True
        assert data["data"]["items"][0]["quantity"] == 3

    def test_update_quantity_total_recalculates(self, client, auth_headers):
        """Bug-catcher: total must update correctly after quantity change."""
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": MOUSE_ID, "quantity": 2})
        res = client.patch(f"/api/cart/item/{MOUSE_ID}", headers=auth_headers,
                           json={"quantity": 5})
        data = res.get_json()
        expected = round(29.99 * 5, 2)
        assert data["data"]["total_price"] == expected

    def test_update_quantity_exceeds_stock(self, client, auth_headers):
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": LOW_STOCK_ID, "quantity": 1})
        res = client.patch(f"/api/cart/item/{LOW_STOCK_ID}", headers=auth_headers,
                           json={"quantity": 100})
        assert res.status_code == 409

    def test_update_item_not_in_cart(self, client, auth_headers):
        res = client.patch(f"/api/cart/item/{IN_STOCK_ID}", headers=auth_headers,
                           json={"quantity": 2})
        assert res.status_code == 404


class TestRemoveCartItem:
    def test_remove_item_success(self, client, auth_headers):
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": IN_STOCK_ID, "quantity": 1})
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": MOUSE_ID, "quantity": 1})

        res = client.delete(f"/api/cart/item/{IN_STOCK_ID}", headers=auth_headers)
        data = res.get_json()
        assert res.status_code == 200
        assert data["data"]["item_count"] == 1
        product_ids = [i["product_id"] for i in data["data"]["items"]]
        assert IN_STOCK_ID not in product_ids

    def test_remove_item_not_in_cart(self, client, auth_headers):
        res = client.delete(f"/api/cart/item/{IN_STOCK_ID}", headers=auth_headers)
        assert res.status_code == 404

    def test_remove_item_unauthenticated(self, client):
        res = client.delete(f"/api/cart/item/{IN_STOCK_ID}")
        assert res.status_code == 401


class TestClearCart:
    def test_clear_cart_success(self, client, auth_headers):
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": IN_STOCK_ID, "quantity": 1})
        res = client.delete("/api/cart/clear", headers=auth_headers)
        data = res.get_json()
        assert res.status_code == 200
        assert data["data"]["item_count"] == 0
        assert data["data"]["total_price"] == 0.0
        assert data["data"]["items"] == []

    def test_clear_already_empty_cart(self, client, auth_headers):
        res = client.delete("/api/cart/clear", headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json()["data"]["item_count"] == 0
