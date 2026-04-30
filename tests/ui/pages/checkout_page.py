import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from .base_page import BasePage


class CheckoutPage(BasePage):
    URL = "/checkout"

    def open(self):
        self.navigate(self.URL)
        # Wait briefly for the spinner to finish and either:
        #   (a) checkout content appears  → cart has items, stay here
        #   (b) page redirects away       → empty cart, already gone
        # We poll for up to 5 s; if the URL changes we return immediately
        # so that test_empty_cart_redirects_away_from_checkout still works.
        for _ in range(25):
            time.sleep(0.2)
            if "/checkout" not in self.driver.current_url:
                return self  # redirected away — let the test assert the URL
            try:
                el = self.driver.find_element(
                    By.CSS_SELECTOR, '[data-testid="checkout-total-amount"]'
                )
                if el.is_displayed():
                    return self
            except Exception:
                pass
        return self

    def get_order_total(self) -> str:
        # Wait until the async loadCheckout() replaces the initial "$0.00"
        WebDriverWait(self.driver, 10).until(
            lambda d: d.find_element(
                By.CSS_SELECTOR, '[data-testid="checkout-total-amount"]'
            ).text.strip() not in ("$0.00", "")
        )
        return self.get_text("checkout-total-amount")

    def select_payment_method(self, value: str):
        from selenium.webdriver.support.ui import Select
        el = self.find("select-payment-method")
        Select(el).select_by_value(value)

    def click_place_order(self):
        self.click("btn-place-order")

    def get_error_message(self) -> str:
        return self.get_text("error-message")

    def is_error_displayed(self) -> bool:
        el = self.wait_for("error-message")
        return "d-none" not in el.get_attribute("class")

    def click_back_to_cart(self):
        self.click("link-back-to-cart")

    def get_item_names(self) -> list[str]:
        from selenium.webdriver.common.by import By
        els = self.driver.find_elements(
            By.CSS_SELECTOR, '[data-testid^="checkout-item-name-"]'
        )
        return [e.text for e in els]

    # ─── Payment Form Methods ───────────────────────────────────────────

    def click_next_to_payment(self):
        """Click Next button to go to payment form step."""
        self.click("btn-next-to-payment")

    def click_back_from_payment(self):
        """Click Back button to return to payment method selection."""
        self.click("btn-back-from-payment")

    def is_card_form_visible(self) -> bool:
        """Check if credit card form is visible."""
        return self.is_displayed("step2-payment")

    def is_method_selection_visible(self) -> bool:
        """Check if payment method selection is visible."""
        return self.is_displayed("step1-method")

    def enter_card_number(self, card_num: str):
        """Enter credit card number."""
        self.type_text("input-card-number", card_num)

    def enter_card_expiry(self, expiry: str):
        """Enter card expiry in MM/YY format."""
        self.type_text("input-card-expiry", expiry)

    def enter_card_cvv(self, cvv: str):
        """Enter card CVV."""
        self.type_text("input-card-cvv", cvv)

    def get_card_form_error(self) -> str:
        """Get error message from card form."""
        return self.get_text("card-form-error")

    def is_card_form_error_displayed(self) -> bool:
        """Check if card form error is displayed."""
        try:
            el = self.find("card-form-error")
            return "d-none" not in el.get_attribute("class")
        except Exception:
            return False

    def submit_card_form(self):
        """Submit the card form via JS click on the submit button.

        Selenium's WebElement.click() does not reliably fire the form 'submit'
        event on all Chrome/chromedriver combinations. Using JS click is more
        reliable because it goes through the browser's event loop the same way
        a real user click does.
        """
        btn = self.wait_for_visible("btn-place-order")
        self.driver.execute_script("arguments[0].click();", btn)

    def fill_and_submit_card(self, card_num: str, expiry: str, cvv: str):
        """Fill all card fields then submit. Call after click_next_to_payment()."""
        self.enter_card_number(card_num)
        self.enter_card_expiry(expiry)
        self.enter_card_cvv(cvv)
        self.submit_card_form()

