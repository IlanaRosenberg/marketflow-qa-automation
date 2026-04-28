/**
 * MarketFlow API client.
 * Automatically attaches JWT token from localStorage to every request.
 * All methods return parsed JSON: { success, data, error }
 */
const api = (() => {
  const TOKEN_KEY = "marketflow_token";

  function getHeaders(extra = {}) {
    const headers = { "Content-Type": "application/json", ...extra };
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return headers;
  }

  async function request(method, url, body = null) {
    const opts = { method, headers: getHeaders() };
    if (body !== null) opts.body = JSON.stringify(body);
    try {
      const response = await fetch(url, opts);
      const json = await response.json();
      return json;
    } catch (err) {
      return { success: false, data: null, error: "Network error" };
    }
  }

  return {
    get:    (url)         => request("GET",    url),
    post:   (url, body)   => request("POST",   url, body),
    patch:  (url, body)   => request("PATCH",  url, body),
    delete: (url)         => request("DELETE", url),
    getToken: ()          => localStorage.getItem(TOKEN_KEY),
    setToken: (t)         => localStorage.setItem(TOKEN_KEY, t),
    clearToken: ()        => localStorage.removeItem(TOKEN_KEY),
  };
})();

// Sync navbar on every page load
(function syncNavbar() {
  const raw = localStorage.getItem("marketflow_user");
  const loginLink    = document.getElementById("nav-login-link");
  const userInfo     = document.getElementById("nav-user-info");
  const logoutItem   = document.getElementById("nav-logout-item");
  const usernameEl   = document.getElementById("nav-username");
  const myOrdersItem = document.getElementById("nav-my-orders-item");

  if (raw && localStorage.getItem("marketflow_token")) {
    try {
      const user = JSON.parse(raw);
      if (loginLink)    loginLink.parentElement.classList.add("d-none");
      if (userInfo)     userInfo.classList.remove("d-none");
      if (logoutItem)   logoutItem.classList.remove("d-none");
      if (myOrdersItem) myOrdersItem.classList.remove("d-none");
      if (usernameEl)   usernameEl.textContent = `Hi, ${user.username}`;
    } catch (_) {}
  }
})();

// Refresh cart count badge on load
(async function refreshCartCount() {
  if (!localStorage.getItem("marketflow_token")) return;
  try {
    const res = await api.get("/api/cart/");
    if (res.success) updateCartCount(res.data.item_count);
  } catch (_) {}
})();
