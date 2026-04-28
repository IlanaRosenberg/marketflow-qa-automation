import time
from .base_page import BasePage


class ProductListPage(BasePage):
    URL = "/"

    def open(self):
        self.navigate(self.URL)
        self.wait_for_visible("products-list")
        time.sleep(0.5)  # wait for async product load
        return self

    def search(self, query: str):
        self.type_text("search-box", query)
        time.sleep(0.6)  # debounce delay

    def select_sort(self, value: str):
        from selenium.webdriver.support.ui import Select
        el = self.find("sort-dropdown")
        Select(el).select_by_value(value)
        time.sleep(0.3)

    def select_category(self, value: str):
        from selenium.webdriver.support.ui import Select
        el = self.find("category-filter")
        Select(el).select_by_value(value)
        time.sleep(0.3)

    def get_product_names(self) -> list[str]:
        cards = self.driver.find_elements(
            *self._by_testid_prefix("product-name-")
        )
        return [c.text for c in cards]

    def _by_testid_prefix(self, prefix: str):
        from selenium.webdriver.common.by import By
        return By.CSS_SELECTOR, f'[data-testid^="{prefix}"]'

    def get_product_count(self) -> int:
        from selenium.webdriver.common.by import By
        cards = self.driver.find_elements(
            By.CSS_SELECTOR, '[data-testid^="product-card-"]'
        )
        return len(cards)

    def get_product_name(self, product_id: int) -> str:
        return self.get_text(f"product-name-{product_id}")

    def get_product_price(self, product_id: int) -> str:
        return self.get_text(f"product-price-{product_id}")

    def click_product_detail(self, product_id: int):
        self.click(f"product-link-{product_id}")

    def click_add_to_cart(self, product_id: int):
        self.click(f"btn-add-to-cart-{product_id}")

    def is_add_to_cart_enabled(self, product_id: int) -> bool:
        return self.is_enabled(f"btn-add-to-cart-{product_id}")

    def is_no_results_displayed(self) -> bool:
        el = self.wait_for("no-results")
        return "d-none" not in el.get_attribute("class")

    def click_next_page(self):
        self.click("btn-next-page")
        time.sleep(0.3)

    def click_prev_page(self):
        self.click("btn-prev-page")
        time.sleep(0.3)

    def get_current_page_text(self) -> str:
        return self.get_text("current-page")

    def get_cart_count(self) -> int:
        return int(self.get_text("cart-count"))
