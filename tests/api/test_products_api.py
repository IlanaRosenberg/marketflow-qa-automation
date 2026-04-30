"""
API tests for product endpoints.
Covers: list, detail, create — including pagination, search, category filter, sort.
"""
import pytest
import allure

pytestmark = [pytest.mark.api, pytest.mark.regression]

IN_STOCK_ID = 1      # Laptop Pro, stock=10
OUT_OF_STOCK_ID = 3  # USB-C Cable, stock=0
BOOK_PRODUCT_ID = 9  # The QA Engineer Handbook, category=Books


@allure.feature("Products")
@allure.story("List Products")
class TestListProducts:
    @pytest.mark.smoke
    @pytest.mark.sanity
    @allure.title("List products returns 20 total with 10 per page")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_list_products_success(self, client):
        res = client.get("/api/products/")
        data = res.get_json()
        assert res.status_code == 200
        assert data["success"] is True
        assert isinstance(data["data"]["products"], list)
        assert data["data"]["total"] == 20  # 20 products seeded
        assert data["data"]["page"] == 1
        assert len(data["data"]["products"]) == 10  # default per_page=10

    def test_list_products_returns_correct_count_per_page(self, client):
        res = client.get("/api/products/?per_page=3&page=1")
        data = res.get_json()
        assert res.status_code == 200
        assert len(data["data"]["products"]) == 3
        assert data["data"]["total"] == 20  # 20 products seeded

    def test_list_products_pagination_page2(self, client):
        res = client.get("/api/products/?per_page=5&page=2")
        data = res.get_json()
        assert res.status_code == 200
        assert len(data["data"]["products"]) == 5
        assert data["data"]["total"] == 20

    def test_list_products_search_returns_only_matches(self, client):
        res = client.get("/api/products/?search=Laptop")
        data = res.get_json()
        assert res.status_code == 200
        products = data["data"]["products"]
        assert len(products) >= 1
        # All returned products must contain "laptop" in name or description
        for p in products:
            assert "laptop" in (p["name"] + (p["description"] or "")).lower()
        # Products not matching should NOT appear
        names = [p["name"] for p in products]
        assert "Wireless Mouse" not in names

    def test_list_products_search_no_match(self, client):
        res = client.get("/api/products/?search=XYZNOTFOUND123")
        data = res.get_json()
        assert res.status_code == 200
        assert data["data"]["products"] == []
        assert data["data"]["total"] == 0

    def test_list_products_category_filter(self, client):
        res = client.get("/api/products/?category=Sports")
        data = res.get_json()
        assert res.status_code == 200
        products = data["data"]["products"]
        assert len(products) == 2  # Running Shoes + Yoga Mat
        for p in products:
            assert p["category"] == "Sports"

    def test_list_products_sort_by_price_asc(self, client):
        res = client.get("/api/products/?sort=price")
        data = res.get_json()
        prices = [p["price"] for p in data["data"]["products"]]
        assert prices == sorted(prices)

    def test_list_products_sort_by_price_desc(self, client):
        res = client.get("/api/products/?sort=-price")
        data = res.get_json()
        prices = [p["price"] for p in data["data"]["products"]]
        assert prices == sorted(prices, reverse=True)

    def test_list_products_invalid_page(self, client):
        res = client.get("/api/products/?page=0")
        assert res.status_code == 400
        assert res.get_json()["success"] is False

    def test_list_products_invalid_per_page(self, client):
        res = client.get("/api/products/?per_page=0")
        assert res.status_code == 400
        assert res.get_json()["success"] is False

    def test_list_products_no_auth_required(self, client):
        # Public endpoint — no token needed
        res = client.get("/api/products/")
        assert res.status_code == 200


@allure.feature("Products")
@allure.story("Product Detail")
class TestGetProduct:
    @pytest.mark.smoke
    @pytest.mark.sanity
    @allure.title("GET /products/{id} returns correct product data")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_get_product_by_id_success(self, client):
        res = client.get(f"/api/products/{IN_STOCK_ID}")
        data = res.get_json()
        assert res.status_code == 200
        assert data["success"] is True
        assert data["data"]["id"] == IN_STOCK_ID
        assert data["data"]["name"] == "Laptop Pro"
        assert data["data"]["price"] == 1299.99
        assert data["data"]["stock_quantity"] == 10

    def test_get_product_out_of_stock(self, client):
        res = client.get(f"/api/products/{OUT_OF_STOCK_ID}")
        data = res.get_json()
        assert res.status_code == 200
        assert data["data"]["stock_quantity"] == 0

    def test_get_product_not_found(self, client):
        res = client.get("/api/products/99999")
        data = res.get_json()
        assert res.status_code == 404
        assert data["success"] is False
        assert data["error"] is not None


@allure.feature("Products")
@allure.story("Create Product")
class TestCreateProduct:
    @pytest.mark.sanity
    @allure.title("Create product with valid data returns 201")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_product_success(self, client, auth_headers):
        res = client.post("/api/products/", headers=auth_headers, json={
            "name": "Test Gadget",
            "description": "A test product",
            "price": 49.99,
            "stock_quantity": 5,
            "sku": "TEST-NEW-001",
            "category": "Electronics",
        })
        data = res.get_json()
        assert res.status_code == 201
        assert data["success"] is True
        assert data["data"]["name"] == "Test Gadget"
        assert data["data"]["sku"] == "TEST-NEW-001"

    def test_create_product_duplicate_sku(self, client, auth_headers):
        res = client.post("/api/products/", headers=auth_headers, json={
            "name": "Duplicate SKU Product",
            "price": 9.99,
            "stock_quantity": 1,
            "sku": "LAPTOP-001",  # already exists
        })
        assert res.status_code == 400
        assert res.get_json()["success"] is False
        assert "sku" in res.get_json()["error"].lower()

    def test_create_product_unauthenticated(self, client):
        res = client.post("/api/products/", json={
            "name": "Sneaky Product",
            "price": 9.99,
            "stock_quantity": 1,
            "sku": "SNEAKY-001",
        })
        assert res.status_code == 401

    def test_create_product_missing_name(self, client, auth_headers):
        res = client.post("/api/products/", headers=auth_headers, json={
            "price": 9.99,
            "stock_quantity": 1,
            "sku": "NO-NAME-001",
        })
        assert res.status_code == 400
        assert res.get_json()["success"] is False

    def test_create_product_negative_price(self, client, auth_headers):
        res = client.post("/api/products/", headers=auth_headers, json={
            "name": "Negative Price",
            "price": -5.0,
            "stock_quantity": 1,
            "sku": "NEG-001",
        })
        assert res.status_code == 400

    def test_create_product_missing_sku(self, client, auth_headers):
        res = client.post("/api/products/", headers=auth_headers, json={
            "name": "No SKU Product",
            "price": 19.99,
            "stock_quantity": 5,
        })
        assert res.status_code == 400
        assert res.get_json()["success"] is False


@allure.feature("Products")
@allure.story("List Products — Combined Filters")
class TestListProductsCombinedFilters:
    @allure.title("Search + category filter together returns only matching results")
    @allure.severity(allure.severity_level.NORMAL)
    def test_search_and_category_together(self, client):
        """Bug-catcher: combined ?search=&category= must apply both constraints."""
        res = client.get("/api/products/?search=Mouse&category=Electronics")
        data = res.get_json()
        assert res.status_code == 200
        products = data["data"]["products"]
        assert len(products) >= 1
        for p in products:
            assert p["category"] == "Electronics"
            assert "mouse" in (p["name"] + (p["description"] or "")).lower()

    @allure.title("Category + sort filters together return sorted results")
    @allure.severity(allure.severity_level.NORMAL)
    def test_category_and_sort_together(self, client):
        res = client.get("/api/products/?category=Electronics&sort=price")
        data = res.get_json()
        assert res.status_code == 200
        products = data["data"]["products"]
        assert all(p["category"] == "Electronics" for p in products)
        prices = [p["price"] for p in products]
        assert prices == sorted(prices)

    @allure.title("Page beyond total returns empty list not error")
    @allure.severity(allure.severity_level.MINOR)
    def test_page_beyond_total_returns_empty(self, client):
        """Requesting a page number past the last page should return [] not 404."""
        res = client.get("/api/products/?page=999")
        data = res.get_json()
        assert res.status_code == 200
        assert data["data"]["products"] == []

    @allure.title("Default sort is by name ascending")
    @allure.severity(allure.severity_level.MINOR)
    def test_default_sort_is_by_name(self, client):
        res = client.get("/api/products/?per_page=20")
        data = res.get_json()
        names = [p["name"] for p in data["data"]["products"]]
        assert names == sorted(names, key=str.lower)
