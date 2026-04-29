"""
Intentional API test failures — known bugs tracked for the Allure report.

These tests are marked xfail(strict=True) so they appear in Allure as
KNOWN FAILURES (orange) rather than blocking the suite. Each one documents
a real gap between the API spec and the current implementation.
"""
import pytest
import allure
from tests.conftest import attach_response

pytestmark = pytest.mark.api


@allure.feature("Products")
@allure.story("Known Failures — Unimplemented Features")
class TestKnownFailures:
    """
    Four documented bugs visible in the Allure report as XFAIL.
    Each test describes the expected behaviour, the actual behaviour,
    and the business impact — the same information you would put in a
    real bug ticket.
    """

    @pytest.mark.xfail(strict=True, reason="BUG-001: GET /api/products/ should support ?in_stock=true filter — not yet implemented")
    @allure.title("[BUG-001] ?in_stock=true filter is not implemented")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.label("bug_id", "BUG-001")
    def test_list_products_in_stock_filter_not_implemented(self, client):
        """
        Regression: The product listing endpoint should support filtering
        by availability (?in_stock=true), returning only products with
        stock_quantity > 0. Currently the parameter is silently ignored.
        """
        res = client.get("/api/products/?in_stock=true")
        data = res.get_json()
        assert res.status_code == 200
        products = data["data"]["products"]
        # All returned products must have stock > 0
        for p in products:
            assert p["stock_quantity"] > 0, (
                f"Product '{p['name']}' (id={p['id']}) has stock=0 "
                f"but was returned with ?in_stock=true filter"
            )

    @pytest.mark.xfail(strict=True, reason="BUG-002: GET /api/products/ should support ?min_price and ?max_price filters — not implemented")
    @allure.title("[BUG-002] ?min_price / ?max_price range filter is not implemented")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.label("bug_id", "BUG-002")
    def test_list_products_price_range_filter_not_implemented(self, client):
        """
        Feature gap: The product listing endpoint should support price-range
        filtering via ?min_price=50&max_price=200, returning only products whose
        price falls within that range. Currently the parameters are silently ignored
        and all products are returned regardless of price.
        """
        res = client.get("/api/products/?min_price=50&max_price=200")
        data = res.get_json()
        assert res.status_code == 200
        products = data["data"]["products"]
        # All returned products must be within the price range
        for p in products:
            assert 50.0 <= p["price"] <= 200.0, (
                f"Product '{p['name']}' price ${p['price']} is outside "
                f"?min_price=50&max_price=200 filter range"
            )

    @pytest.mark.xfail(strict=True, reason="BUG-003: GET /api/products/ should support ?sort=stock to sort by availability — not implemented")
    @allure.title("[BUG-003] ?sort=stock sorting is not implemented")
    @allure.severity(allure.severity_level.MINOR)
    @allure.label("bug_id", "BUG-003")
    def test_list_products_sort_by_stock_not_implemented(self, client):
        """
        Feature gap: The sort parameter should accept 'stock' and '-stock'
        to order products by stock_quantity ascending/descending.
        Currently only 'name', 'price', '-price' are supported; passing
        'stock' falls through silently to the default name-sort, meaning
        the result is NOT sorted by stock.
        """
        res = client.get("/api/products/?sort=stock")
        data = res.get_json()
        assert res.status_code == 200
        stocks = [p["stock_quantity"] for p in data["data"]["products"]]
        # Should be sorted ascending by stock_quantity
        assert stocks == sorted(stocks), (
            f"Products are not sorted by stock_quantity ascending. Got: {stocks}"
        )


@allure.feature("Authentication")
@allure.story("Known Failures — Unimplemented Features")
class TestAuthKnownFailures:

    @pytest.mark.xfail(strict=True, reason="BUG-004: POST /api/auth/register has no maximum length validation on username — accepts up to 500+ chars")
    @pytest.mark.api
    @allure.title("[BUG-004] Username has no maximum length validation")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.label("bug_id", "BUG-004")
    def test_register_username_max_length_not_validated(self, client):
        """
        Validation gap: POST /api/auth/register accepts usernames of any length.
        Industry standard is a maximum of 50-100 characters. Accepting 500+
        character usernames wastes database storage, can break UI display
        elements, and may be exploited for denial-of-service through repeated
        registrations with huge payloads.

        Expected: 400 Bad Request when username exceeds maximum allowed length.
        Actual:   201 Created — 500-character username is stored successfully.
        """
        long_username = "a" * 500
        res = client.post("/api/auth/register", json={
            "username": long_username,
            "email": "toolong@test.com",
            "password": "Pass123!",
        })
        attach_response(res, "Register 500-char username response")
        assert res.status_code == 400, (
            f"Expected 400 for username with {len(long_username)} characters "
            f"but got {res.status_code}. No maximum length is enforced."
        )


@allure.feature("Products")
@allure.story("Known Failures — Unimplemented Features")
class TestProductKnownFailures:

    @pytest.mark.xfail(strict=True, reason="BUG-005: POST /api/products/ allows price=0 — free products can be created unintentionally")
    @pytest.mark.api
    @allure.title("[BUG-005] Product creation allows price=0 without warning")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.label("bug_id", "BUG-005")
    def test_create_product_zero_price_not_rejected(self, client, auth_headers):
        """
        Validation gap: POST /api/products/ accepts price=0, creating a
        product that is effectively free. While a zero-price product may be
        intentional in some business models, no warning or explicit flag is
        required, making it trivially easy to accidentally set a price to 0.
        A minimum price validation (price > 0) or an explicit 'is_free'
        boolean flag would prevent accidental free listings.

        Expected: 400 Bad Request or at minimum a validation warning for price=0.
        Actual:   201 Created — product with price=$0.00 is accepted.
        """
        res = client.post("/api/products/", headers=auth_headers, json={
            "name": "Accidentally Free Product",
            "price": 0,
            "stock_quantity": 10,
            "sku": "FREE-BUG-005",
        })
        attach_response(res, "Create product price=0 response")
        assert res.status_code == 400, (
            f"Expected 400 for price=0 but got {res.status_code}. "
            f"Products with zero price should be explicitly flagged or rejected."
        )
