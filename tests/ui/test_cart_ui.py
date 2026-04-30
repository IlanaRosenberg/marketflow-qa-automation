"""
UI tests for the cart page.
"""
import pytest
import allure
import time
from tests.ui.pages.cart_page import CartPage
from tests.ui.pages.product_list_page import ProductListPage

pytestmark = [pytest.mark.ui, pytest.mark.regression]

IN_STOCK_ID = 1   # Laptop Pro
MOUSE_ID = 2      # Wireless Mouse


@pytest.fixture(autouse=True)
def require_server(live_app):
    pass


def add_product_via_api(driver, base_url, product_id, quantity=1):
    """Add product to cart via JS fetch. Uses execute_async_script callback pattern."""
    driver.execute_async_script(
        """
        const cb = arguments[arguments.length - 1];
        const base_url = arguments[0];
        const product_id = arguments[1];
        const quantity = arguments[2];
        const token = localStorage.getItem('marketflow_token');
        fetch(base_url + '/api/cart/add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
            body: JSON.stringify({product_id: product_id, quantity: quantity})
        }).then(r => r.json()).then(cb).catch(cb);
        """,
        base_url, product_id, quantity
    )


@allure.feature("Cart")
@allure.story("Cart UI")
class TestCartUI:
    @allure.title("Empty cart displays empty state message")
    @allure.severity(allure.severity_level.NORMAL)
    def test_empty_cart_shows_empty_message(self, logged_in_driver, base_url):
        driver = logged_in_driver
        page = CartPage(driver, base_url).open()
        assert page.is_cart_empty()

    @pytest.mark.smoke
    @pytest.mark.sanity
    @allure.title("Added product appears in cart")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_add_product_appears_in_cart(self, logged_in_driver, base_url):
        driver = logged_in_driver
        add_product_via_api(driver, base_url, IN_STOCK_ID, 1)
        page = CartPage(driver, base_url).open()
        assert not page.is_cart_empty()
        assert page.is_product_in_cart(IN_STOCK_ID)

    def test_cart_shows_correct_item_count(self, logged_in_driver, base_url):
        driver = logged_in_driver
        add_product_via_api(driver, base_url, IN_STOCK_ID, 1)
        add_product_via_api(driver, base_url, MOUSE_ID, 1)
        page = CartPage(driver, base_url).open()
        assert page.get_item_count() == 2

    def test_remove_item_from_cart(self, logged_in_driver, base_url):
        driver = logged_in_driver
        add_product_via_api(driver, base_url, IN_STOCK_ID, 1)
        add_product_via_api(driver, base_url, MOUSE_ID, 1)
        page = CartPage(driver, base_url).open()
        page.remove_item(IN_STOCK_ID)
        time.sleep(0.5)
        assert not page.is_product_in_cart(IN_STOCK_ID)
        assert page.get_item_count() == 1

    def test_clear_cart_empties_all_items(self, logged_in_driver, base_url):
        driver = logged_in_driver
        add_product_via_api(driver, base_url, IN_STOCK_ID, 1)
        add_product_via_api(driver, base_url, MOUSE_ID, 1)
        page = CartPage(driver, base_url).open()
        page.click_clear_cart()
        time.sleep(0.5)
        assert page.is_cart_empty()

    def test_checkout_button_navigates_to_checkout(self, logged_in_driver, base_url):
        driver = logged_in_driver
        add_product_via_api(driver, base_url, IN_STOCK_ID, 1)
        page = CartPage(driver, base_url).open()
        page.click_checkout()
        time.sleep(0.5)
        assert "/checkout" in driver.current_url

    def test_unauthenticated_cart_redirects_to_login(self, driver, base_url):
        page = CartPage(driver, base_url)
        page.navigate("/cart")
        time.sleep(0.5)
        assert "/login" in driver.current_url

    def test_continue_shopping_link_works(self, logged_in_driver, base_url):
        driver = logged_in_driver
        page = CartPage(driver, base_url).open()
        page.click_continue_shopping()
        time.sleep(0.3)
        assert "/cart" not in driver.current_url

    @allure.title("Updating quantity in cart recalculates total price")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_quantity_recalculates_total(self, logged_in_driver, base_url):
        """Bug-catcher: changing item quantity on the cart page must update the total."""
        driver = logged_in_driver
        add_product_via_api(driver, base_url, MOUSE_ID, 1)
        page = CartPage(driver, base_url).open()
        total_before = page.get_total_price()
        page.set_item_quantity(MOUSE_ID, 3)
        total_after = page.get_total_price()
        assert total_before != total_after, (
            "Total price must change when item quantity is updated from 1 to 3"
        )
        assert "89.97" in total_after  # 29.99 * 3

    @allure.title("Cart item count in navbar updates after adding product")
    @allure.severity(allure.severity_level.NORMAL)
    def test_cart_badge_updates_after_add(self, logged_in_driver, base_url):
        """Bug-catcher: navbar cart badge must reflect the current number of distinct cart items."""
        driver = logged_in_driver
        from tests.ui.pages.product_list_page import ProductListPage
        page = ProductListPage(driver, base_url).open()
        count_before = page.get_cart_count()
        add_product_via_api(driver, base_url, MOUSE_ID, 1)
        driver.refresh()
        time.sleep(0.5)
        count_after = page.get_cart_count()
        assert count_after == count_before + 1
