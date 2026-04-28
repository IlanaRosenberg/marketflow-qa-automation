"""
UI tests for the checkout flow.
"""
import pytest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tests.ui.pages.checkout_page import CheckoutPage
from tests.ui.pages.order_history_page import OrderHistoryPage

pytestmark = [pytest.mark.ui, pytest.mark.regression]

IN_STOCK_ID = 1   # Laptop Pro
MOUSE_ID = 2      # Wireless Mouse


@pytest.fixture(autouse=True)
def require_server(live_app):
    pass


def add_via_api(driver, base_url, product_id, quantity=1):
    """Add a product to cart via fetch. Passes args as script arguments to avoid f-string JS issues."""
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
        }).then(() => cb()).catch(() => cb());
        """,
        base_url, product_id, quantity
    )


class TestCheckoutUI:
    def test_checkout_displays_order_summary(self, logged_in_driver, base_url):
        driver = logged_in_driver
        add_via_api(driver, base_url, IN_STOCK_ID, 1)
        page = CheckoutPage(driver, base_url).open()
        items = page.get_item_names()
        assert len(items) == 1
        assert "Laptop Pro" in items[0]

    def test_checkout_displays_correct_total(self, logged_in_driver, base_url):
        driver = logged_in_driver
        add_via_api(driver, base_url, IN_STOCK_ID, 1)
        page = CheckoutPage(driver, base_url).open()
        total = page.get_order_total()
        assert "1299.99" in total

    def test_checkout_multi_product_total(self, logged_in_driver, base_url):
        driver = logged_in_driver
        add_via_api(driver, base_url, IN_STOCK_ID, 1)
        add_via_api(driver, base_url, MOUSE_ID, 2)
        page = CheckoutPage(driver, base_url).open()
        total_text = page.get_order_total()
        # 1299.99 + 29.99*2 = 1359.97
        assert "1359.97" in total_text

    def test_checkout_payment_method_selection(self, logged_in_driver, base_url):
        driver = logged_in_driver
        add_via_api(driver, base_url, MOUSE_ID, 1)
        page = CheckoutPage(driver, base_url).open()
        page.select_payment_method("paypal")
        # No error should appear
        assert not page.is_error_displayed()

    # ─── Payment Form Validation Tests ──────────────────────────────────

    def test_payment_form_hidden_initially(self, logged_in_driver, base_url):
        """Payment form should be hidden on page load."""
        driver = logged_in_driver
        add_via_api(driver, base_url, MOUSE_ID, 1)
        page = CheckoutPage(driver, base_url).open()
        assert page.is_method_selection_visible()
        assert not page.is_card_form_visible()

    def test_payment_form_shows_after_next_button(self, logged_in_driver, base_url):
        """Payment form should appear when Next button is clicked."""
        driver = logged_in_driver
        add_via_api(driver, base_url, MOUSE_ID, 1)
        page = CheckoutPage(driver, base_url).open()
        page.click_next_to_payment()
        time.sleep(0.3)
        assert page.is_card_form_visible()

    def test_checkout_back_button_returns_to_method(self, logged_in_driver, base_url):
        """Back button should return to payment method selection."""
        driver = logged_in_driver
        add_via_api(driver, base_url, MOUSE_ID, 1)
        page = CheckoutPage(driver, base_url).open()
        page.click_next_to_payment()
        time.sleep(0.3)
        page.click_back_from_payment()
        time.sleep(0.3)
        assert page.is_method_selection_visible()
        assert not page.is_card_form_visible()

    def test_invalid_card_number_rejected(self, logged_in_driver, base_url):
        """Card number with fewer than 13 digits must show a validation error."""
        driver = logged_in_driver
        add_via_api(driver, base_url, MOUSE_ID, 1)
        page = CheckoutPage(driver, base_url).open()
        page.click_next_to_payment()
        time.sleep(0.3)
        # 4 digits — clearly below the 13-digit minimum
        page.enter_card_number("1234")
        page.enter_card_expiry("12/30")
        page.enter_card_cvv("123")
        page.submit_card_form()
        time.sleep(0.3)
        assert page.is_card_form_error_displayed()
        error = page.get_card_form_error()
        assert "digit" in error.lower() or "invalid" in error.lower() or "number" in error.lower()

    def test_expired_card_rejected(self, logged_in_driver, base_url):
        """Expired card should show error."""
        driver = logged_in_driver
        add_via_api(driver, base_url, MOUSE_ID, 1)
        page = CheckoutPage(driver, base_url).open()
        page.click_next_to_payment()
        time.sleep(0.3)
        page.enter_card_number("4111111111111111")
        page.enter_card_expiry("12/20")  # Expired
        page.enter_card_cvv("123")
        page.submit_card_form()
        time.sleep(0.3)
        assert page.is_card_form_error_displayed()
        error = page.get_card_form_error()
        assert "expired" in error.lower()

    def test_invalid_cvv_rejected(self, logged_in_driver, base_url):
        """CVV with fewer than 3 digits must show a validation error."""
        driver = logged_in_driver
        add_via_api(driver, base_url, MOUSE_ID, 1)
        page = CheckoutPage(driver, base_url).open()
        page.click_next_to_payment()
        time.sleep(0.3)
        page.enter_card_number("4111111111111111")
        page.enter_card_expiry("12/30")
        page.enter_card_cvv("1")  # 1 digit — clearly below the 3-digit minimum
        page.submit_card_form()
        time.sleep(0.3)
        assert page.is_card_form_error_displayed()
        error = page.get_card_form_error()
        assert "cvv" in error.lower() or "digit" in error.lower() or "required" in error.lower()

    def test_valid_card_completes_checkout(self, logged_in_driver, base_url):
        """Valid card details should complete checkout successfully."""
        driver = logged_in_driver
        add_via_api(driver, base_url, MOUSE_ID, 1)
        page = CheckoutPage(driver, base_url).open()
        page.click_next_to_payment()
        time.sleep(0.3)
        # Fill valid card (test number 4111111111111111)
        page.fill_and_submit_card("4111111111111111", "12/30", "123")
        time.sleep(0.5)
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="thank-you-message"]'))
        )
        banner = driver.find_element("css selector", '[data-testid="thank-you-message"]')
        assert "thank you" in banner.text.lower()

    # ─── Original Tests (Updated for multi-step form) ───────────────────

    @pytest.mark.smoke
    @pytest.mark.sanity
    def test_place_order_shows_thank_you_banner(self, logged_in_driver, base_url):
        """Original test updated for multi-step payment form."""
        driver = logged_in_driver
        add_via_api(driver, base_url, MOUSE_ID, 1)
        page = CheckoutPage(driver, base_url).open()
        # Go through payment form with valid card
        page.click_next_to_payment()
        time.sleep(0.3)
        page.fill_and_submit_card("4111111111111111", "12/30", "123")
        time.sleep(0.5)
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="thank-you-message"]'))
        )
        banner = driver.find_element("css selector", '[data-testid="thank-you-message"]')
        assert "thank you" in banner.text.lower()

    def test_place_order_success_redirects_to_my_orders(self, logged_in_driver, base_url):
        """Original test updated for multi-step payment form."""
        driver = logged_in_driver
        add_via_api(driver, base_url, MOUSE_ID, 1)
        page = CheckoutPage(driver, base_url).open()
        # Go through payment form with valid card
        page.click_next_to_payment()
        time.sleep(0.3)
        page.fill_and_submit_card("4111111111111111", "12/30", "123")
        time.sleep(2.5)
        assert "/my-orders" in driver.current_url

    def test_place_order_clears_cart(self, logged_in_driver, base_url):
        """Original test updated for multi-step payment form."""
        driver = logged_in_driver
        add_via_api(driver, base_url, MOUSE_ID, 1)
        page = CheckoutPage(driver, base_url).open()
        # Go through payment form with valid card
        page.click_next_to_payment()
        time.sleep(0.3)
        page.fill_and_submit_card("4111111111111111", "12/30", "123")
        time.sleep(2.5)
        cart_count_el = driver.find_element("css selector", '[data-testid="cart-count"]')
        assert cart_count_el.text == "0"

    def test_order_appears_in_history_after_checkout(self, logged_in_driver, base_url):
        """Original test updated for multi-step payment form."""
        driver = logged_in_driver
        add_via_api(driver, base_url, MOUSE_ID, 1)
        page = CheckoutPage(driver, base_url).open()
        # Go through payment form with valid card
        page.click_next_to_payment()
        time.sleep(0.3)
        page.fill_and_submit_card("4111111111111111", "12/30", "123")
        time.sleep(2.5)
        # Redirected to /my-orders — wait for at least one order card
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid^="my-order-card-"]'))
        )
        cards = driver.find_elements(By.CSS_SELECTOR, '[data-testid^="my-order-card-"]')
        assert len(cards) >= 1

    def test_back_to_cart_link_works(self, logged_in_driver, base_url):
        driver = logged_in_driver
        add_via_api(driver, base_url, MOUSE_ID, 1)
        page = CheckoutPage(driver, base_url).open()
        page.click_back_to_cart()
        time.sleep(0.5)
        assert "/cart" in driver.current_url

    def test_empty_cart_redirects_away_from_checkout(self, logged_in_driver, base_url):
        """Checkout page should redirect if cart is empty."""
        driver = logged_in_driver
        # Clear cart first
        driver.execute_async_script(
            f"""
            const cb = arguments[arguments.length - 1];
            const token = localStorage.getItem('marketflow_token');
            fetch('{base_url}/api/cart/clear', {{
                method: 'DELETE',
                headers: {{'Authorization': 'Bearer ' + token}}
            }}).then(() => cb());
            """
        )
        CheckoutPage(driver, base_url).open()
        time.sleep(1)
        assert "/checkout" not in driver.current_url
