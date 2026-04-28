from .base_page import BasePage


class ProductDetailPage(BasePage):
    def open(self, product_id: int):
        self.navigate(f"/products/{product_id}")
        self.wait_for_visible("product-title")
        return self

    def get_title(self) -> str:
        return self.get_text("product-title")

    def get_description(self) -> str:
        return self.get_text("product-description")

    def get_sku(self) -> str:
        return self.get_text("product-sku")

    def get_price(self) -> str:
        return self.get_text("product-price")

    def get_stock(self) -> str:
        return self.get_text("product-stock")

    def set_quantity(self, qty: int):
        self.type_text("input-quantity", str(qty))

    def click_add_to_cart(self):
        self.click("btn-add-to-cart")

    def is_add_to_cart_enabled(self) -> bool:
        return self.is_enabled("btn-add-to-cart")

    def is_success_displayed(self) -> bool:
        el = self.wait_for("success-message")
        return "d-none" not in el.get_attribute("class")

    def is_error_displayed(self) -> bool:
        el = self.wait_for("error-message")
        return "d-none" not in el.get_attribute("class")

    def get_error_message(self) -> str:
        return self.get_text("error-message")

    def click_back_to_products(self):
        self.click("link-back-to-products")
