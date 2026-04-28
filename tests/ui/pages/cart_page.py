from .base_page import BasePage


class CartPage(BasePage):
    URL = "/cart"

    def open(self):
        self.navigate(self.URL)
        self.wait_for_visible("page-cart")
        return self

    def get_item_count(self) -> int:
        return int(self.get_text("item-count"))

    def get_total_price(self) -> str:
        return self.get_text("total-amount")

    def get_item_quantity(self, product_id: int) -> int:
        el = self.find(f"input-quantity-{product_id}")
        return int(el.get_attribute("value"))

    def set_item_quantity(self, product_id: int, qty: int):
        self.type_text(f"input-quantity-{product_id}", str(qty))
        # Trigger change event
        from selenium.webdriver.common.keys import Keys
        self.find(f"input-quantity-{product_id}").send_keys(Keys.TAB)
        import time; time.sleep(0.5)

    def remove_item(self, product_id: int):
        self.click(f"btn-remove-item-{product_id}")
        import time; time.sleep(0.3)

    def click_clear_cart(self):
        self.click("btn-clear-cart")
        import time; time.sleep(0.3)

    def click_checkout(self):
        self.click("btn-checkout")

    def is_cart_empty(self) -> bool:
        el = self.wait_for("cart-empty")
        return "d-none" not in el.get_attribute("class")

    def is_product_in_cart(self, product_id: int) -> bool:
        return self.is_displayed(f"cart-item-row-{product_id}")

    def get_product_name(self, product_id: int) -> str:
        return self.get_text(f"cart-product-name-{product_id}")

    def click_continue_shopping(self):
        self.click("link-continue-shopping")
