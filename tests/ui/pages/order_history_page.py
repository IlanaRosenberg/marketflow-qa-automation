from .base_page import BasePage


class OrderHistoryPage(BasePage):
    URL = "/order-history"

    def open(self):
        self.navigate(self.URL)
        self.wait_for_visible("page-order-history")
        return self

    def get_order_count(self) -> int:
        from selenium.webdriver.common.by import By
        rows = self.driver.find_elements(
            By.CSS_SELECTOR, '[data-testid^="order-row-"]'
        )
        return len(rows)

    def get_order_status(self, order_id: int) -> str:
        return self.get_text(f"order-status-{order_id}")

    def get_order_total(self, order_id: int) -> str:
        return self.get_text(f"order-total-{order_id}")

    def click_view_order(self, order_id: int):
        self.click(f"btn-view-order-{order_id}")

    def click_cancel_order(self, order_id: int):
        self.click(f"btn-cancel-order-{order_id}")

    def is_cancel_enabled(self, order_id: int) -> bool:
        return self.is_enabled(f"btn-cancel-order-{order_id}")

    def is_no_orders_displayed(self) -> bool:
        el = self.wait_for("no-orders")
        return "d-none" not in el.get_attribute("class")
