def validate_create_product(data: dict) -> str | None:
    """Returns error message string or None if valid."""
    if not data:
        return "Request body must be valid JSON"
    if not (data.get("name") or "").strip():
        return "Product name is required"
    if data.get("price") is None:
        return "Price is required"
    try:
        price = float(data["price"])
        if price < 0:
            return "Price must be a non-negative number"
    except (TypeError, ValueError):
        return "Price must be a number"
    if data.get("stock_quantity") is None:
        return "stock_quantity is required"
    try:
        qty = int(data["stock_quantity"])
        if qty < 0:
            return "stock_quantity must be non-negative"
    except (TypeError, ValueError):
        return "stock_quantity must be an integer"
    if not (data.get("sku") or "").strip():
        return "SKU is required"
    return None
