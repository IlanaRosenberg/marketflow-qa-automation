import pytest
import allure
import threading
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from app import create_app
from app.database import db as _db
from app.models import CartItem
from seed_data.seed import seed_db

PORT = 5001
BASE_URL = f"http://localhost:{PORT}"

TEST_USER = {
    "email": "testuser1@example.com",
    "password": "Password123!",
    "username": "testuser1",
}

# Shared app reference used by the cart-clear fixture
_flask_app = None


@pytest.fixture(scope="session")
def live_app():
    """Start a real Flask server in a background thread for Selenium tests."""
    global _flask_app
    flask_app = create_app("testing")
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test_ui.db"

    with flask_app.app_context():
        _db.create_all()
        seed_db()

    thread = threading.Thread(
        target=lambda: flask_app.run(port=PORT, debug=False, use_reloader=False),
        daemon=True,
    )
    thread.start()
    time.sleep(1.5)
    _flask_app = flask_app
    yield flask_app

    with flask_app.app_context():
        _db.drop_all()


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="function")
def driver():
    """Headless Chrome WebDriver. Captures a screenshot on test failure."""
    options = Options()
    # options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(5)

    yield drv

    # Attach screenshot to Allure if the test failed
    if hasattr(drv, "session_id") and drv.session_id:
        try:
            screenshot = drv.get_screenshot_as_png()
            allure.attach(
                screenshot,
                name="Screenshot on failure",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception:
            pass

    try:
        drv.quit()
    except Exception:
        pass


@pytest.fixture(scope="function")
def logged_in_driver(driver, live_app, base_url):
    """Driver with testuser1 already logged in (token set in localStorage).

    Before each test:
    - Clears testuser1's cart in the DB
    - Resets stock for products frequently used in UI tests so stock
      depletion from prior checkout tests does not cause failures
    """
    with live_app.app_context():
        from app.models import User, Product
        user = User.query.filter_by(email=TEST_USER["email"]).first()
        if user:
            CartItem.query.filter_by(user_id=user.id).delete()

        # Reset stock for products used in UI checkout/cart tests
        stock_resets = {
            1: 10,   # Laptop Pro
            2: 50,   # Wireless Mouse
            4: 5,    # Monitor
            5: 20,   # Mechanical Keyboard
            6: 15,   # Running Shoes
            7: 30,   # Yoga Mat
            8: 1,    # Coffee Maker (keep at 1 — low stock boundary)
            11: 8,   # 4K Webcam
            12: 12,  # Wireless Headphones
        }
        for pid, stock in stock_resets.items():
            p = Product.query.get(pid)
            if p:
                p.stock_quantity = stock

        _db.session.commit()

    driver.get(f"{base_url}/login")
    time.sleep(0.5)
    driver.find_element("css selector", '[data-testid="input-email"]').send_keys(TEST_USER["email"])
    driver.find_element("css selector", '[data-testid="input-password"]').send_keys(TEST_USER["password"])
    driver.find_element("css selector", '[data-testid="btn-login"]').click()
    time.sleep(1)

    # Attach the JWT token that the login stored in localStorage
    try:
        token = driver.execute_script("return localStorage.getItem('marketflow_token')")
        if token:
            allure.attach(
                token,
                name="JWT Token — UI login (testuser1)",
                attachment_type=allure.attachment_type.TEXT,
            )
    except Exception:
        pass

    return driver
