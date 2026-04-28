"""
Cross-layer data consistency tests.
Validates that API state matches DB state and business rules hold across operations.
"""
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.regression]

IN_STOCK_ID = 1    # Laptop Pro: $1299.99, stock=10
MOUSE_ID = 2       # Wireless Mouse: $29.99, stock=50
BOOK_ID = 9        # Book: $14.99, stock=100


class TestCartConsistency:
    def test_api_cart_matches_db_cart(self, client, auth_headers, app):
        """Cart returned by API must match CartItem rows in the database."""
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": IN_STOCK_ID, "quantity": 3})
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": MOUSE_ID, "quantity": 2})

        api_cart = client.get("/api/cart/", headers=auth_headers).get_json()["data"]
        api_item_count = api_cart["item_count"]
        api_total = api_cart["total_price"]

        with app.app_context():
            from app.models import CartItem, User
            user = User.query.filter_by(username="testuser1").first()
            db_items = CartItem.query.filter_by(user_id=user.id).all()
            db_total = round(sum(i.quantity * i.product.price for i in db_items), 2)

        assert api_item_count == len(db_items)
        assert api_total == db_total

    def test_failed_add_leaves_db_unchanged(self, client, auth_headers, app):
        """Failed add (out-of-stock) must not create any CartItem in DB."""
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": 3, "quantity": 1})  # product 3 = out of stock

        with app.app_context():
            from app.models import CartItem, User
            user = User.query.filter_by(username="testuser1").first()
            items = CartItem.query.filter_by(user_id=user.id).all()
        assert len(items) == 0


class TestOrderConsistency:
    def test_order_total_matches_cart_total_before_checkout(self, client, auth_headers):
        """Order total in DB must exactly match cart total before checkout."""
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": IN_STOCK_ID, "quantity": 2})
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": BOOK_ID, "quantity": 4})

        cart_total = client.get("/api/cart/", headers=auth_headers)\
            .get_json()["data"]["total_price"]
        order_total = client.post("/api/orders/checkout", headers=auth_headers,
                                  json={"payment_method": "credit_card"})\
            .get_json()["data"]["total_price"]

        assert order_total == cart_total

    def test_stock_decremented_correctly_in_db(self, client, auth_headers, app):
        """DB stock must decrease by exact ordered quantity after checkout."""
        with app.app_context():
            from app.models import Product
            before = Product.query.get(IN_STOCK_ID).stock_quantity

        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": IN_STOCK_ID, "quantity": 3})
        client.post("/api/orders/checkout", headers=auth_headers,
                    json={"payment_method": "credit_card"})

        with app.app_context():
            from app.models import Product
            after = Product.query.get(IN_STOCK_ID).stock_quantity

        assert after == before - 3

    def test_cart_empty_in_db_after_checkout(self, client, auth_headers, app):
        """CartItem rows for user must be deleted after checkout."""
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": MOUSE_ID, "quantity": 1})
        client.post("/api/orders/checkout", headers=auth_headers,
                    json={"payment_method": "credit_card"})

        with app.app_context():
            from app.models import CartItem, User
            user = User.query.filter_by(username="testuser1").first()
            items = CartItem.query.filter_by(user_id=user.id).all()
        assert len(items) == 0

    def test_order_items_recorded_correctly_in_db(self, client, auth_headers, app):
        """OrderItem rows must match the products and quantities ordered."""
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": IN_STOCK_ID, "quantity": 2})
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": BOOK_ID, "quantity": 5})
        order_id = client.post("/api/orders/checkout", headers=auth_headers,
                               json={"payment_method": "credit_card"})\
            .get_json()["data"]["id"]

        with app.app_context():
            from app.models import OrderItem
            items = OrderItem.query.filter_by(order_id=order_id).all()
            items_by_product = {i.product_id: i for i in items}

        assert len(items) == 2
        assert items_by_product[IN_STOCK_ID].quantity == 2
        assert items_by_product[BOOK_ID].quantity == 5

    def test_user_isolation_in_db(self, client, auth_headers, auth_headers_user2, app):
        """User1's orders must not appear in user2's order list."""
        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": MOUSE_ID, "quantity": 1})
        client.post("/api/orders/checkout", headers=auth_headers,
                    json={"payment_method": "credit_card"})

        user2_orders = client.get("/api/orders/", headers=auth_headers_user2)\
            .get_json()["data"]["total"]
        assert user2_orders == 0

    def test_cancel_status_persists_in_db(self, client, auth_headers, app):
        """Cancelled order status must be 'cancelled' in DB, not 'completed'."""
        from app.models import Order
        from app.database import db

        client.post("/api/cart/add", headers=auth_headers,
                    json={"product_id": MOUSE_ID, "quantity": 1})
        order_id = client.post("/api/orders/checkout", headers=auth_headers,
                               json={"payment_method": "credit_card"})\
            .get_json()["data"]["id"]

        with app.app_context():
            order = Order.query.get(order_id)
            order.status = "pending"
            db.session.commit()

        client.post(f"/api/orders/{order_id}/cancel", headers=auth_headers)

        with app.app_context():
            order = Order.query.get(order_id)
            assert order.status == "cancelled"


class TestProductSearchConsistency:
    def test_search_api_count_matches_result_length(self, client):
        """The 'total' field in search results must match len(products)."""
        res = client.get("/api/products/?search=Mouse&per_page=50")
        data = res.get_json()["data"]
        assert data["total"] == len(data["products"])

    def test_category_filter_consistent_with_db(self, client, app):
        """API category filter must return same count as DB query."""
        api_res = client.get("/api/products/?category=Sports&per_page=50")
        api_count = api_res.get_json()["data"]["total"]

        with app.app_context():
            from app.models import Product
            db_count = Product.query.filter(
                Product.category.ilike("%Sports%")
            ).count()

        assert api_count == db_count
