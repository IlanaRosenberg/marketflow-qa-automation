"""
Intentional API test failures — known bugs tracked for the Allure report.

These tests are marked xfail(strict=False) so they appear in Allure as
KNOWN FAILURES (orange) rather than blocking the suite. Each one documents
a real gap between the API spec and the current implementation.
"""
import pytest

pytestmark = pytest.mark.api


class TestKnownFailures:
    """
    Three intentional failures that represent real open bugs.
    They show up in Allure as FAILED / XFAIL so the team can see
    what is not yet implemented.
    """

    @pytest.mark.xfail(strict=True, reason="BUG-001: GET /api/products/ should support ?in_stock=true filter — not yet implemented")
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

    @pytest.mark.xfail(strict=True, reason="BUG-002: POST /api/products/ should reject stock_quantity < 0 — validation missing")
    def test_create_product_negative_stock_rejected(self, client, auth_headers):
        """
        Regression: Creating a product with negative stock should return 400.
        Currently the API accepts it and persists a negative stock value,
        which breaks inventory logic downstream.
        """
        res = client.post("/api/products/", headers=auth_headers, json={
            "name": "Broken Stock Product",
            "description": "This should be rejected",
            "price": 19.99,
            "stock_quantity": -5,
            "sku": "NEG-STOCK-001",
            "category": "Electronics",
        })
        assert res.status_code == 400, (
            f"Expected 400 for negative stock_quantity, got {res.status_code}"
        )
        assert res.get_json()["success"] is False

    @pytest.mark.xfail(strict=True, reason="BUG-003: GET /api/products/ should return 400 for per_page > 100 — missing upper-bound check")
    def test_list_products_per_page_upper_bound_not_enforced(self, client):
        """
        Regression: The per_page parameter should be capped at 100.
        The route checks per_page < 1 but has no upper-bound check (> 100 is allowed).
        Requesting per_page=9999 should return 400, not a massive result set.
        """
        res = client.get("/api/products/?per_page=9999")
        assert res.status_code == 400, (
            f"Expected 400 for per_page=9999 (above max 100), got {res.status_code}"
        )
        assert res.get_json()["success"] is False
