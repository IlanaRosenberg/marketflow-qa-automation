def validate_add_to_cart(data: dict) -> str | None:
    if not data:
        return "Request body must be valid JSON"
    if data.get("product_id") is None:
        return "product_id is required"
    try:
        product_id = int(data["product_id"])
        if product_id < 1:
            return "product_id must be a positive integer"
    except (TypeError, ValueError):
        return "product_id must be an integer"
    quantity = data.get("quantity", 1)
    try:
        qty = int(quantity)
        if qty < 1:
            return "quantity must be at least 1"
    except (TypeError, ValueError):
        return "quantity must be an integer"
    return None


def validate_update_quantity(data: dict) -> str | None:
    if not data:
        return "Request body must be valid JSON"
    if data.get("quantity") is None:
        return "quantity is required"
    try:
        qty = int(data["quantity"])
        if qty < 1:
            return "quantity must be at least 1"
    except (TypeError, ValueError):
        return "quantity must be an integer"
    return None
