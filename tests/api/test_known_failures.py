"""
Intentional API test failures — known bugs tracked for the Allure report.

These tests are marked xfail(strict=False) so they appear in Allure as
KNOWN FAILURES (orange) rather than blocking the suite. Each one documents
a real gap between the API spec and the current implementation.
"""
import pytest
import allure

pytestmark = pytest.mark.api


@allure.feature("Products")
@allure.story("Known Failures — Unimplemented Features")
class TestKnownFailures:
    """
    Three intentional failures that represent real open bugs.
    They show up in Allure as XFAIL so the team can track
    what is not yet implemented.
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
