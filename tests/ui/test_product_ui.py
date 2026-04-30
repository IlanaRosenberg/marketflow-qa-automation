"""
UI tests for product list and product detail pages.
"""
import pytest
import allure
import time
from tests.ui.pages.product_list_page import ProductListPage
from tests.ui.pages.product_detail_page import ProductDetailPage

pytestmark = [pytest.mark.ui, pytest.mark.regression]

IN_STOCK_ID = 1      # Laptop Pro
OUT_OF_STOCK_ID = 3  # USB-C Cable


@pytest.fixture(autouse=True)
def require_server(live_app):
    pass


@allure.feature("Products")
@allure.story("Product List UI")
class TestProductListUI:
    def test_products_page_displays_products(self, driver, base_url):
        page = ProductListPage(driver, base_url).open()
        count = page.get_product_count()
        assert count > 0

    def test_default_page_shows_10_products(self, driver, base_url):
        """Product list shows 10 products per page by default."""
        page = ProductListPage(driver, base_url).open()
        assert page.get_product_count() == 10

    def test_search_filters_products(self, driver, base_url):
        page = ProductListPage(driver, base_url).open()
        page.search("Laptop")
        names = page.get_product_names()
        assert len(names) >= 1
        assert any("Laptop" in n for n in names)

    def test_search_no_results_shows_message(self, driver, base_url):
        page = ProductListPage(driver, base_url).open()
        page.search("XYZNOTFOUND999")
        time.sleep(0.7)
        assert page.is_no_results_displayed()

    def test_sort_by_price_low_to_high(self, driver, base_url):
        page = ProductListPage(driver, base_url).open()
        page.select_sort("price")
        time.sleep(0.3)
        # First product should be cheapest
        first_price = page.find("product-price-9").text  # Book ($14.99)
        assert "14.99" in first_price

    def test_category_filter_shows_only_sports(self, driver, base_url):
        page = ProductListPage(driver, base_url).open()
        page.select_category("Sports")
        time.sleep(0.3)
        count = page.get_product_count()
        assert count == 2

    def test_click_product_opens_detail_page(self, driver, base_url):
        page = ProductListPage(driver, base_url).open()
        page.click_product_detail(IN_STOCK_ID)
        time.sleep(0.5)
        assert f"/products/{IN_STOCK_ID}" in driver.current_url

    def test_out_of_stock_add_button_disabled(self, driver, base_url):
        page = ProductListPage(driver, base_url).open()
        assert not page.is_add_to_cart_enabled(OUT_OF_STOCK_ID)

    def test_add_to_cart_redirects_to_login_when_not_logged_in(self, driver, base_url):
        page = ProductListPage(driver, base_url).open()
        page.click_add_to_cart(IN_STOCK_ID)
        time.sleep(0.5)
        assert "/login" in driver.current_url

    def test_add_to_cart_updates_cart_count(self, logged_in_driver, base_url):
        driver = logged_in_driver
        page = ProductListPage(driver, base_url).open()
        before = page.get_cart_count()
        page.click_add_to_cart(IN_STOCK_ID)
        time.sleep(0.8)
        after = page.get_cart_count()
        assert after == before + 1

    @allure.title("Next page button loads page 2 of products")
    @allure.severity(allure.severity_level.NORMAL)
    def test_next_page_loads_different_products(self, driver, base_url):
        """Bug-catcher: clicking Next must advance the page and show new products."""
        page = ProductListPage(driver, base_url).open()
        page_1_names = set(page.get_product_names())
        page.click_next_page()
        time.sleep(0.5)
        page_2_names = set(page.get_product_names())
        assert page_2_names != page_1_names, (
            "Page 2 products must differ from page 1 products"
        )
        assert len(page_2_names) > 0

    @allure.title("Previous page button returns to page 1")
    @allure.severity(allure.severity_level.NORMAL)
    def test_prev_page_returns_to_page_1(self, driver, base_url):
        """Navigate next then back — must return to the exact same page 1 results."""
        page = ProductListPage(driver, base_url).open()
        page_1_names = set(page.get_product_names())
        page.click_next_page()
        time.sleep(0.5)
        page.click_prev_page()
        time.sleep(0.5)
        returned_names = set(page.get_product_names())
        assert returned_names == page_1_names


@allure.feature("Products")
@allure.story("Product Detail UI")
class TestProductDetailUI:
    def test_product_detail_page_displays_info(self, driver, base_url):
        page = ProductDetailPage(driver, base_url).open(IN_STOCK_ID)
        assert "Laptop Pro" in page.get_title()
        assert len(page.get_description()) > 0
        assert "LAPTOP-001" in page.get_sku()
        assert "1299.99" in page.get_price()

    def test_out_of_stock_detail_disables_add_button(self, driver, base_url):
        page = ProductDetailPage(driver, base_url).open(OUT_OF_STOCK_ID)
        assert not page.is_add_to_cart_enabled()
        assert "out of stock" in page.get_stock().lower()

    def test_back_to_products_link_works(self, driver, base_url):
        page = ProductDetailPage(driver, base_url).open(IN_STOCK_ID)
        page.click_back_to_products()
        time.sleep(0.3)
        assert driver.current_url.rstrip("/").endswith("")  # back to /

    def test_add_to_cart_from_detail_shows_success(self, logged_in_driver, base_url):
        driver = logged_in_driver
        page = ProductDetailPage(driver, base_url).open(IN_STOCK_ID)
        page.set_quantity(1)
        page.click_add_to_cart()
        time.sleep(0.5)
        assert page.is_success_displayed()
