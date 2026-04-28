from .base_page import BasePage


class LoginPage(BasePage):
    URL = "/login"

    def open(self):
        self.navigate(self.URL)
        self.wait_for_visible("login-form")
        return self

    def enter_email(self, email: str):
        self.type_text("input-email", email)

    def enter_password(self, password: str):
        self.type_text("input-password", password)

    def click_login(self):
        self.click("btn-login")

    def login(self, email: str, password: str):
        self.enter_email(email)
        self.enter_password(password)
        self.click_login()

    def get_error_message(self) -> str:
        return self.get_text("error-message")

    def is_error_displayed(self) -> bool:
        el = self.wait_for("error-message")
        return "d-none" not in el.get_attribute("class")

    def click_register_link(self):
        self.click("link-register")

    def is_login_form_displayed(self) -> bool:
        return self.is_displayed("login-form")
