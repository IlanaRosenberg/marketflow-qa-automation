"""
UI tests for authentication flows (login, register, logout).
Uses Page Object Model with data-testid locators.
"""
import pytest
import allure
import time
from tests.ui.pages.login_page import LoginPage
from tests.ui.pages.register_page import RegisterPage

pytestmark = [pytest.mark.ui, pytest.mark.regression]

VALID_EMAIL = "testuser1@example.com"
VALID_PASSWORD = "Password123!"


@pytest.fixture(autouse=True)
def require_server(live_app):
    pass


@allure.feature("Authentication")
@allure.story("Login UI")
class TestLoginUI:
    @allure.title("Login page displays the login form")
    @allure.severity(allure.severity_level.NORMAL)
    def test_login_form_is_displayed(self, driver, base_url):
        page = LoginPage(driver, base_url).open()
        assert page.is_login_form_displayed()

    @pytest.mark.smoke
    @pytest.mark.sanity
    @allure.title("Valid login redirects to home page")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_login_success_redirects_to_home(self, driver, base_url):
        page = LoginPage(driver, base_url).open()
        page.login(VALID_EMAIL, VALID_PASSWORD)
        time.sleep(1)
        assert "/" in driver.current_url
        assert "/login" not in driver.current_url

    def test_login_wrong_password_shows_error(self, driver, base_url):
        page = LoginPage(driver, base_url).open()
        page.login(VALID_EMAIL, "WrongPassword!")
        time.sleep(0.5)
        assert page.is_error_displayed()
        error = page.get_error_message()
        assert len(error) > 0

    def test_login_nonexistent_user_shows_error(self, driver, base_url):
        page = LoginPage(driver, base_url).open()
        page.login("ghost@example.com", "Password123!")
        time.sleep(0.5)
        assert page.is_error_displayed()

    def test_login_stores_token_in_localstorage(self, driver, base_url):
        page = LoginPage(driver, base_url).open()
        page.login(VALID_EMAIL, VALID_PASSWORD)
        time.sleep(1)
        token = driver.execute_script("return localStorage.getItem('marketflow_token')")
        assert token is not None
        assert len(token) > 10

    def test_navbar_shows_username_after_login(self, driver, base_url):
        page = LoginPage(driver, base_url).open()
        page.login(VALID_EMAIL, VALID_PASSWORD)
        time.sleep(1)
        username_el = driver.find_element("css selector", '[data-testid="nav-username"]')
        assert "testuser1" in username_el.text

    def test_register_link_navigates_to_register(self, driver, base_url):
        page = LoginPage(driver, base_url).open()
        page.click_register_link()
        time.sleep(0.5)
        assert "/register" in driver.current_url


@allure.feature("Authentication")
@allure.story("Register UI")
class TestRegisterUI:
    def test_register_success_redirects_to_login(self, driver, base_url):
        page = RegisterPage(driver, base_url).open()
        page.register(
            username="newuiuser",
            email="newuiuser@example.com",
            password="Pass123!",
            first_name="New",
            last_name="UIUser",
        )
        time.sleep(1)
        assert "/login" in driver.current_url

    def test_register_duplicate_email_shows_error(self, driver, base_url):
        page = RegisterPage(driver, base_url).open()
        page.register(
            username="uniqueuser",
            email=VALID_EMAIL,  # already registered
            password="Pass123!",
        )
        time.sleep(0.5)
        assert page.is_error_displayed()
        assert len(page.get_error_message()) > 0

    def test_register_login_link_navigates_to_login(self, driver, base_url):
        page = RegisterPage(driver, base_url).open()
        page.click_login_link()
        time.sleep(0.5)
        assert "/login" in driver.current_url
