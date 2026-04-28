# MarketFlow QA Test Documentation

## Overview

MarketFlow uses a three-layer test strategy across **105 automated tests**:

| Layer | Runner | Count | Scope |
|-------|--------|-------|-------|
| API Tests | pytest + Flask test client | 90 | All REST endpoints, business rules, auth |
| Integration Tests | pytest + Flask test client | 15 | Cross-layer consistency, full user journeys |
| UI Tests | pytest + Selenium | 37 | Browser flows, POM, data-testid locators |

---

## QA Testing Strategy

### Philosophy: Assert Exact State, Not Just "No Error"

Every test verifies **specific resulting state**, not merely that a request returned 200. For example:

- After adding to cart → assert `item_count` increased by exactly 1 and `total_price` increased by `price × qty`
- After checkout → assert cart `item_count == 0` AND `product.stock_quantity` decreased by ordered amount
- After cancelling → assert `GET /orders/{id}` returns `status == "cancelled"`
- After a failed add → assert `item_count` is unchanged (silent failure detection)

This approach catches bugs that don't surface as crashes: wrong totals, stock not decremented, cart not cleared, user isolation leaks.

### Test Isolation

API and integration tests use a **function-scoped app fixture** that creates a fresh in-memory SQLite database, seeds it with predictable data, and drops all tables after each test. No state leaks between tests.

UI tests use a **session-scoped live server** on port 5001 with a file-backed SQLite DB. Each test gets a fresh Chrome driver but shares the same server.

### Seed Data Contract

Tests rely on fixed product IDs with known properties:

| ID | Product | Stock | Purpose |
|----|---------|-------|---------|
| 1 | Laptop Pro ($1299.99) | 10 | Primary test product |
| 2 | Wireless Mouse ($29.99) | 50 | Secondary product, high stock |
| 3 | USB-C Cable ($9.99) | **0** | Out-of-stock scenario |
| 8 | Coffee Maker ($79.99) | **1** | Low-stock boundary test |
| 10 | Desk Lamp ($44.99) | **0** | Second out-of-stock product |

Two test users: `testuser1@example.com` and `testuser2@example.com` (both `Password123!`).

---

## API Tests (`tests/api/`)

### `test_auth_api.py` — 16 tests

**Coverage:** Register, Login, Logout, /me endpoints

| Test | Purpose |
|------|---------|
| `test_register_success` | New user creates account; response contains id, username, email |
| `test_register_duplicate_username` | Duplicate username returns 400 with "username" in error |
| `test_register_duplicate_email` | Duplicate email returns 400 with "email" in error |
| `test_register_missing_username` | Missing required field returns 400 |
| `test_register_invalid_email` | Email without @ returns 400 |
| `test_register_short_password` | Password < 6 chars returns 400 |
| `test_login_success` | Valid credentials return JWT token, user_id, username |
| `test_login_wrong_password` | Wrong password returns 401 with data=null |
| `test_login_nonexistent_user` | Unknown email returns 401 |
| `test_login_missing_email` | Missing email field returns 400 |
| `test_login_missing_password` | Missing password field returns 400 |
| `test_logout_success` | Valid token logout returns 200 |
| `test_logout_no_token` | No token returns 401 |
| `test_logout_invalid_token` | Fake token returns 401 |
| `test_get_me_authenticated` | Returns current user's username and email |
| `test_get_me_unauthenticated` | No token returns 401 |

---

### `test_products_api.py` — 19 tests

**Coverage:** List/search/filter/sort/paginate products; get by ID; create product

| Test | Purpose |
|------|---------|
| `test_list_products_default` | Returns 10 seeded products, correct total |
| `test_list_products_pagination` | per_page=3 returns 3 items, correct pages count |
| `test_list_products_page_2` | Second page returns expected items |
| `test_list_products_search` | `?search=Laptop` returns only Laptop Pro |
| `test_list_products_search_no_match` | Non-matching search returns empty products list |
| `test_list_products_category_filter` | `?category=Sports` returns only Sports products |
| `test_list_products_sort_price_asc` | `?sort=price` — first item is cheapest |
| `test_list_products_sort_price_desc` | `?sort=-price` — first item is most expensive |
| `test_list_products_sort_name` | `?sort=name` — products in alphabetical order |
| `test_list_products_per_page_too_large` | `?per_page=200` returns 400 |
| `test_get_product_success` | Returns correct product fields for ID=1 |
| `test_get_out_of_stock_product` | Product 3 has `stock_quantity == 0` |
| `test_get_product_not_found` | ID=99999 returns 404 with success=false |
| `test_create_product_success` | Authenticated user creates product; returns 201 |
| `test_create_product_unauthenticated` | No token returns 401 |
| `test_create_product_missing_name` | Missing required field returns 400 |
| `test_create_product_duplicate_sku` | Duplicate SKU returns 400 |
| `test_create_product_negative_price` | Negative price returns 400 |
| `test_list_products_count_matches_db` | API total matches DB row count |

---

### `test_cart_api.py` — 18 tests

**Coverage:** View, add, update quantity, remove item, clear cart; bug-catching assertions

| Test | Purpose |
|------|---------|
| `test_get_empty_cart` | Fresh user has 0 items, 0 total |
| `test_add_to_cart_success` | Add 1 item; item_count == 1 |
| `test_add_to_cart_increases_item_count` | **Bug-catcher:** item_count increments exactly by 1 |
| `test_add_to_cart_out_of_stock_fails` | Product 3 (stock=0) returns 400 |
| `test_add_to_cart_out_of_stock_does_not_change_cart` | **Bug-catcher:** failed add keeps item_count == 0 |
| `test_add_same_product_twice_increases_quantity_not_rows` | **Bug-catcher:** second add merges quantity, not duplicate row |
| `test_add_multiple_products_correct_total` | Total = sum of price × qty across all items |
| `test_update_quantity_success` | PATCH updates quantity to new value |
| `test_update_quantity_total_recalculates` | **Bug-catcher:** total_price = price × new_qty exactly |
| `test_update_quantity_zero_or_negative_fails` | qty <= 0 returns 400 |
| `test_remove_item_success` | DELETE removes item; item_count decreases |
| `test_remove_nonexistent_item` | Remove unknown product_id returns 404 |
| `test_clear_cart_success` | DELETE /clear returns 0 items and 0 total |
| `test_get_cart_unauthenticated` | No token returns 401 |
| `test_add_to_cart_unauthenticated` | No token returns 401 |
| `test_add_exceeds_stock` | Requesting more than stock_quantity returns 400 |
| `test_cart_total_with_multiple_quantities` | Multi-qty multi-product total is calculated correctly |
| `test_add_low_stock_product` | Product 8 (stock=1) can be added exactly once |

---

### `test_orders_api.py` — 18 tests

**Coverage:** Checkout, list orders, order detail, cancel; bug-catching state assertions

| Test | Purpose |
|------|---------|
| `test_checkout_success` | Returns 201, status=completed, correct total, items array |
| `test_checkout_cart_cleared_after_order` | **Bug-catcher:** cart item_count == 0 after checkout |
| `test_checkout_stock_decremented_after_order` | **Bug-catcher:** product stock_quantity decreased by ordered qty |
| `test_checkout_order_total_matches_cart_total` | **Bug-catcher:** order total == cart total before checkout |
| `test_checkout_empty_cart_fails` | Empty cart returns 400 with "empty" in error |
| `test_checkout_unauthenticated` | No token returns 401 |
| `test_checkout_multi_product_items_recorded` | Order contains correct product_ids in items array |
| `test_list_orders_empty` | New user has 0 orders |
| `test_list_orders_after_checkout` | Order count increases by 1 after checkout |
| `test_list_orders_status_filter` | `?status=completed` returns only completed orders |
| `test_list_orders_invalid_status` | Unknown status value returns 400 |
| `test_list_orders_unauthenticated` | No token returns 401 |
| `test_list_orders_only_own_orders` | **Bug-catcher:** user2 sees 0 orders after user1 checks out |
| `test_get_order_detail_success` | Returns order with items array |
| `test_get_order_detail_not_found` | ID=99999 returns 404 |
| `test_get_order_detail_not_owned_by_user` | **Bug-catcher:** user2 cannot see user1's order (returns 404) |
| `test_get_order_detail_unauthenticated` | No token returns 401 |
| `test_cancel_pending_order_success` | Pending order → cancelled status |
| `test_cancel_completed_order_success` | Completed order can also be cancelled |
| `test_cancelled_order_status_persists` | **Bug-catcher:** GET after cancel shows status == "cancelled" |
| `test_cannot_cancel_already_cancelled_order` | **Bug-catcher:** second cancel returns 400 |
| `test_cancel_order_not_found` | ID=99999 returns 404 |
| `test_cancel_order_unauthenticated` | No token returns 401 |

---

### `test_error_cases.py` — 11 tests

**Coverage:** Response format contract, malformed input, JWT edge cases, boundary values

| Test | Purpose |
|------|---------|
| `test_error_response_has_required_fields` | All errors: success=false, data=null, error=string |
| `test_success_response_has_required_fields` | All successes: success=true, error=null |
| `test_malformed_json_register` | Non-JSON body returns 400 |
| `test_malformed_json_login` | Broken JSON returns 400 |
| `test_empty_body_add_to_cart` | Null body returns 400 |
| `test_expired_jwt_token` | Token with past `exp` returns 401 with "expired" in error |
| `test_invalid_jwt_signature` | Token signed with wrong secret returns 401 |
| `test_malformed_jwt_format` | Not a valid JWT structure returns 401 |
| `test_bearer_prefix_missing` | Token without "Bearer " prefix returns 401 |
| `test_product_id_zero` | ID=0 returns 404 |
| `test_per_page_too_large` | per_page=200 returns 400 |

---

## Integration Tests (`tests/integration/`)

### `test_end_to_end.py` — 5 tests

**Coverage:** Full user journeys through the complete application stack

| Test | Journey |
|------|---------|
| `test_register_login_browse_cart_checkout` | New user registers → logs in → browses 10 products → adds book × 2 → verifies cart total → checks out → verifies order in history |
| `test_multi_product_order_total_is_correct` | Adds Laptop × 1 + Mouse × 3, verifies order total equals sum of prices |
| `test_unauthenticated_user_cannot_access_cart` | GET /api/cart/ without token returns 401 |
| `test_search_add_checkout_flow` | Searches for "Keyboard" → adds to cart → checks out → verifies order exists |
| `test_cancel_order_flow` | Checks out → cancels order → verifies status == "cancelled" |

---

### `test_data_consistency.py` — 9 tests

**Coverage:** API response state vs. database state validation

| Test | Validates |
|------|-----------|
| `test_api_cart_matches_db_cart` | Cart item_count and total_price from API == rows and sum in DB |
| `test_failed_add_leaves_db_unchanged` | Out-of-stock add creates 0 CartItem rows in DB |
| `test_order_total_matches_cart_total_before_checkout` | Order total_price == cart total_price exactly |
| `test_stock_decremented_in_db_after_checkout` | product.stock_quantity in DB decreases by ordered qty |
| `test_cart_empty_in_db_after_checkout` | CartItem rows for user are deleted after checkout |
| `test_order_items_recorded_correctly` | OrderItem rows match quantities and prices from cart |
| `test_user_isolation_in_db` | User1's CartItems are not visible to user2 via API |
| `test_cancel_persists_in_db` | Order.status == "cancelled" in DB after cancel API call |
| `test_search_count_matches_db` | Products returned by search API equals DB row count for that keyword |

---

## UI Tests (`tests/ui/`)

UI tests start a live Flask server on port 5001 automatically. Chrome runs in headless mode using Selenium's built-in driver manager.

**Run:** `pytest tests/ui/ -v`

### Page Object Model (POM)

All page objects extend `BasePage` which provides:
- `_by_testid(testid)` — returns `(By.CSS_SELECTOR, '[data-testid="X"]')` locator
- `wait_for_visible()`, `wait_for_clickable()` — explicit WebDriverWait wrappers
- `type_text()`, `click()`, `get_text()`, `is_displayed()` — safe action helpers

All HTML elements use `data-testid` attributes for stable locators independent of CSS class changes.

### `test_auth_ui.py` — 10 tests

| Test | Scenario |
|------|---------|
| `test_login_page_loads` | Login form elements are visible |
| `test_login_success_redirects` | Valid credentials redirect to products page |
| `test_login_sets_token_in_localstorage` | Token present in localStorage after login |
| `test_login_shows_username_in_navbar` | Navbar displays "Hi, testuser1" after login |
| `test_login_wrong_password_shows_error` | Wrong password displays error-message element |
| `test_login_empty_fields_shows_error` | Empty form shows validation error |
| `test_register_page_loads` | Register form elements are visible |
| `test_register_success_redirects` | Valid registration redirects to login or home |
| `test_logout_clears_session` | Logout navigates to login page, token removed |
| `test_protected_page_redirects_to_login` | Unauthenticated /cart access redirects to /login |

---

### `test_product_ui.py` — 14 tests

| Test | Scenario |
|------|---------|
| `test_product_list_loads` | Products grid renders with correct count |
| `test_product_cards_show_name_price` | Each card shows product name and price |
| `test_product_images_displayed` | Product cards render img elements |
| `test_search_filters_products` | Typing in search-box updates displayed products |
| `test_search_no_results_shows_empty_state` | No-match search shows no-results element |
| `test_category_filter_electronics` | Selecting Electronics shows only Electronics products |
| `test_sort_price_low_to_high` | First product after sort is cheapest |
| `test_sort_price_high_to_low` | First product after sort is most expensive |
| `test_out_of_stock_button_disabled` | Product 3 "Add to Cart" button is disabled |
| `test_product_detail_page_loads` | Clicking product navigates to detail page |
| `test_product_detail_shows_image` | Detail page renders product image |
| `test_add_to_cart_from_list` | Add to Cart increments cart-count badge |
| `test_pagination_controls` | Next/prev buttons navigate between pages |
| `test_cart_summary_panel_appears_after_add` | Cart summary panel becomes visible after first add |

---

### `test_cart_ui.py` — 8 tests

| Test | Scenario |
|------|---------|
| `test_empty_cart_state` | Cart page shows cart-empty element |
| `test_add_product_appears_in_cart` | Added product shows in cart table |
| `test_cart_item_count_updates` | cart-count badge updates after add |
| `test_remove_item_from_cart` | Remove button removes row from cart table |
| `test_clear_cart_empties_table` | Clear Cart shows empty-cart state |
| `test_checkout_button_visible` | Checkout link is visible with items in cart |
| `test_unauthenticated_cart_redirects` | Visiting /cart without login redirects to /login |
| `test_quantity_update_recalculates_total` | Changing quantity input updates total-amount |

---

### `test_checkout_ui.py` — 9 tests

| Test | Scenario |
|------|---------|
| `test_checkout_displays_order_summary` | Checkout page shows item names from cart |
| `test_checkout_displays_correct_total` | Total matches expected price |
| `test_checkout_multi_product_total` | Multi-item total calculated correctly |
| `test_checkout_payment_method_selection` | Selecting PayPal shows no errors |
| `test_place_order_success_shows_thank_you` | "Thank you for your purchase" banner appears |
| `test_place_order_success_redirects_to_orders` | After 2s redirect lands on /my-orders |
| `test_place_order_clears_cart` | cart-count badge shows 0 after order |
| `test_order_appears_in_history_after_checkout` | Order visible in My Orders page |
| `test_back_to_cart_link_works` | Back to Cart navigates to /cart |
| `test_empty_cart_redirects_away_from_checkout` | Visiting /checkout with empty cart redirects |

---

## Running Tests

```bash
# All API + integration tests (no browser required)
pytest tests/api/ tests/integration/ -v

# Single file
pytest tests/api/test_cart_api.py -v

# Single test
pytest tests/api/test_cart_api.py::TestAddToCart::test_add_to_cart_success -v

# By marker
pytest -m api -v
pytest -m integration -v
pytest -m ui -v

# UI tests (requires Google Chrome installed)
pytest tests/ui/ -v

# With coverage
pytest tests/api/ tests/integration/ --cov=app --cov-report=term-missing -v
```

---

## Business Logic Validation

| Rule | Tested by |
|------|-----------|
| Duplicate user registration blocked | `test_register_duplicate_username/email` |
| Wrong password returns 401 | `test_login_wrong_password` |
| JWT token required for protected routes | `test_*_unauthenticated` (across all suites) |
| Out-of-stock product cannot be added to cart | `test_add_to_cart_out_of_stock_fails` |
| Failed add does not mutate cart state | `test_add_to_cart_out_of_stock_does_not_change_cart` |
| Same product added twice merges quantity | `test_add_same_product_twice_increases_quantity_not_rows` |
| Cart total equals sum of price × qty | `test_add_multiple_products_correct_total` |
| Quantity update recalculates total correctly | `test_update_quantity_total_recalculates` |
| Checkout is atomic: stock decrements | `test_checkout_stock_decremented_after_order` |
| Checkout is atomic: cart cleared | `test_checkout_cart_cleared_after_order` |
| Order total matches pre-checkout cart total | `test_checkout_order_total_matches_cart_total` |
| Users cannot see other users' orders | `test_list_orders_only_own_orders` + `test_get_order_detail_not_owned_by_user` |
| Cancelled order stays cancelled | `test_cancelled_order_status_persists` |
| Already-cancelled order cannot be cancelled again | `test_cannot_cancel_already_cancelled_order` |
| API cart state matches DB state | `test_api_cart_matches_db_cart` |
