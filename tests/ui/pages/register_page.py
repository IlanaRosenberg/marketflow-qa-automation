from .base_page import BasePage


class RegisterPage(BasePage):
    URL = "/register"

    def open(self):
        self.navigate(self.URL)
        self.wait_for_visible("register-form")
        return self

    def enter_username(self, username: str):
        self.type_text("input-username", username)

    def enter_email(self, email: str):
        self.type_text("input-email", email)

    def enter_password(self, password: str):
        self.type_text("input-password", password)

    def enter_first_name(self, name: str):
        self.type_text("input-first-name", name)

    def enter_last_name(self, name: str):
        self.type_text("input-last-name", name)

    def click_register(self):
        self.click("btn-register")

    def register(self, username, email, password, first_name="", last_name=""):
        self.enter_username(username)
        self.enter_email(email)
        self.enter_password(password)
        if first_name:
            self.enter_first_name(first_name)
        if last_name:
            self.enter_last_name(last_name)
        self.click_register()

    def get_error_message(self) -> str:
        return self.get_text("error-message")

    def is_error_displayed(self) -> bool:
        el = self.wait_for("error-message")
        return "d-none" not in el.get_attribute("class")

    def click_login_link(self):
        self.click("link-login")
