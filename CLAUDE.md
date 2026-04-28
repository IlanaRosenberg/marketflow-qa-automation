# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start the dev server (seeds DB automatically on first run)
python run.py                          # http://localhost:5000, Swagger at /api/docs

# Run all non-UI tests (90 API + 15 integration = 105 tests)
pytest tests/api/ tests/integration/ -v

# Run a single test file
pytest tests/api/test_cart_api.py -v

# Run a single test
pytest tests/api/test_cart_api.py::TestAddToCart::test_add_to_cart_success -v

# Run by marker
pytest -m api -v
pytest -m integration -v
pytest -m ui -v

# UI tests (requires Chrome + chromedriver — starts Flask on port 5001 automatically)
pytest tests/ui/ -v
```

## Architecture

### Request/Response Contract
Every API endpoint returns `{"success": bool, "data": ... | null, "error": "message" | null}`. Helpers `success_response()` and `error_response()` in [app/utils.py](app/utils.py) enforce this. Tests always assert both the status code and the `success` flag.

### Auth Dual Layer
- **API calls**: JWT via `Authorization: Bearer <token>` header. `@jwt_required` decorator (in [app/auth/decorators.py](app/auth/decorators.py)) decodes the token and sets `g.current_user`.
- **UI/session routes**: Flask session cookie. Templates check `session.get("user_id")`. Both layers coexist — the same Flask app serves both.

### Test Isolation
API and integration tests use a **function-scoped** `app` fixture ([tests/conftest.py](tests/conftest.py)) that creates a fresh in-memory SQLite DB, seeds it, runs the test, then drops all tables. No state leaks between tests.

UI tests use a **session-scoped** `live_app` fixture ([tests/ui/conftest.py](tests/ui/conftest.py)) that starts one real Flask server on port 5001 for the entire UI test session (file-based `test_ui.db`). The `driver` fixture is function-scoped (fresh Chrome per test).

### Checkout is Atomic
`POST /api/orders/checkout` runs inside a single `db.session`: stock check → `Order` + `OrderItem` creation → `db.session.flush()` (to get `order.id`) → stock decrement → cart clear → commit. Any failure triggers a full rollback.

### Seed Data Contract
Tests depend on predictable IDs: **Product 3 and 10 are always out-of-stock (stock=0)**; **Product 8 (Coffee Maker) has stock=1** (low-stock boundary). Two users: `testuser1@example.com` and `testuser2@example.com`, both `Password123!`.

### UI Locators
All interactive HTML elements use `data-testid` attributes (e.g., `data-testid="btn-add-to-cart"`). Selenium page objects in [tests/ui/pages/](tests/ui/pages/) use `By.CSS_SELECTOR, '[data-testid="X"]'` exclusively. Dynamic rows include the record ID: `data-testid="cart-item-row-{id}"`.

### Postman / Swagger
- Swagger UI: `http://localhost:5000/api/docs` — all routes have flasgger docstrings
- Postman collection: [docs/MarketFlow.postman_collection.json](docs/MarketFlow.postman_collection.json) — Login request auto-saves `{{token}}` via a test script; Checkout auto-saves `{{order_id}}`
