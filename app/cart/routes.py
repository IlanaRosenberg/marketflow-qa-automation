from flask import Blueprint, request, g
from app.database import db
from app.models import CartItem, Product
from app.utils import success_response, error_response
from app.auth.decorators import jwt_required
from app.cart.schemas import validate_add_to_cart, validate_update_quantity

cart_bp = Blueprint("cart", __name__, url_prefix="/api/cart")


def _cart_summary(user_id):
    items = CartItem.query.filter_by(user_id=user_id).all()
    total = round(sum(i.quantity * i.product.price for i in items if i.product), 2)
    return {
        "items": [i.to_dict() for i in items],
        "total_price": total,
        "item_count": len(items),
    }


@cart_bp.route("/", methods=["GET"])
@jwt_required
def get_cart():
    """
    Get the current user's cart
    ---
    tags:
      - Cart
    security:
      - Bearer: []
    responses:
      200:
        description: Cart contents with total price
      401:
        description: Unauthorized
    """
    return success_response(_cart_summary(g.current_user.id))


@cart_bp.route("/add", methods=["POST"])
@jwt_required
def add_to_cart():
    """
    Add a product to the cart
    ---
    tags:
      - Cart
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [product_id]
          properties:
            product_id:
              type: integer
              example: 1
            quantity:
              type: integer
              default: 1
    responses:
      200:
        description: Cart updated
      400:
        description: Validation error or invalid quantity
      404:
        description: Product not found
      409:
        description: Insufficient stock
    """
    data = request.get_json(silent=True)
    err = validate_add_to_cart(data)
    if err:
        return error_response(err, 400)

    product_id = int(data["product_id"])
    quantity = int(data.get("quantity", 1))

    product = Product.query.get(product_id)
    if not product:
        return error_response("Product not found", 404)

    existing = CartItem.query.filter_by(
        user_id=g.current_user.id, product_id=product_id
    ).first()
    new_total_qty = (existing.quantity if existing else 0) + quantity

    if product.stock_quantity == 0:
        return error_response("Product is out of stock", 409)
    if new_total_qty > product.stock_quantity:
        return error_response(
            f"Insufficient stock. Available: {product.stock_quantity}", 409
        )

    if existing:
        existing.quantity = new_total_qty
    else:
        item = CartItem(
            user_id=g.current_user.id,
            product_id=product_id,
            quantity=quantity,
        )
        db.session.add(item)

    db.session.commit()
    return success_response(_cart_summary(g.current_user.id))


@cart_bp.route("/item/<int:product_id>", methods=["PATCH"])
@jwt_required
def update_cart_item(product_id):
    """
    Update the quantity of a cart item
    ---
    tags:
      - Cart
    security:
      - Bearer: []
    parameters:
      - in: path
        name: product_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [quantity]
          properties:
            quantity:
              type: integer
    responses:
      200:
        description: Cart updated
      400:
        description: Validation error
      404:
        description: Item not in cart
      409:
        description: Insufficient stock
    """
    data = request.get_json(silent=True)
    err = validate_update_quantity(data)
    if err:
        return error_response(err, 400)

    item = CartItem.query.filter_by(
        user_id=g.current_user.id, product_id=product_id
    ).first()
    if not item:
        return error_response("Item not in cart", 404)

    quantity = int(data["quantity"])
    product = Product.query.get(product_id)

    if quantity > product.stock_quantity:
        return error_response(
            f"Insufficient stock. Available: {product.stock_quantity}", 409
        )

    item.quantity = quantity
    db.session.commit()
    return success_response(_cart_summary(g.current_user.id))


@cart_bp.route("/item/<int:product_id>", methods=["DELETE"])
@jwt_required
def remove_cart_item(product_id):
    """
    Remove an item from the cart
    ---
    tags:
      - Cart
    security:
      - Bearer: []
    parameters:
      - in: path
        name: product_id
        type: integer
        required: true
    responses:
      200:
        description: Item removed, cart returned
      404:
        description: Item not in cart
    """
    item = CartItem.query.filter_by(
        user_id=g.current_user.id, product_id=product_id
    ).first()
    if not item:
        return error_response("Item not in cart", 404)

    db.session.delete(item)
    db.session.commit()
    return success_response(_cart_summary(g.current_user.id))


@cart_bp.route("/clear", methods=["DELETE"])
@jwt_required
def clear_cart():
    """
    Clear all items from the cart
    ---
    tags:
      - Cart
    security:
      - Bearer: []
    responses:
      200:
        description: Cart cleared
      401:
        description: Unauthorized
    """
    CartItem.query.filter_by(user_id=g.current_user.id).delete()
    db.session.commit()
    return success_response({"items": [], "total_price": 0.0, "item_count": 0})
