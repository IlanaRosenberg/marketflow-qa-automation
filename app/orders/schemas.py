VALID_PAYMENT_METHODS = {"credit_card", "paypal", "bank_transfer"}


def validate_checkout(data: dict) -> str | None:
    if not data:
        return "Request body must be valid JSON"
    method = data.get("payment_method", "credit_card")
    if method not in VALID_PAYMENT_METHODS:
        return f"Invalid payment method. Valid options: {', '.join(VALID_PAYMENT_METHODS)}"
    return None
