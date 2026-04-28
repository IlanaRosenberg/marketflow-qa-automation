from flask import Blueprint, request, g
from app.database import db
from app.models import CartItem, Order, OrderItem, Product
from app.utils import success_response, error_response
from app.auth.decorators import jwt_required
from app.orders.schemas import validate_checkout

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


@orders_bp.route("/checkout", methods=["POST"])
@jwt_required
def checkout():
    """
    Checkout: create an order from the current cart
    ---
    tags:
      - Orders
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            payment_method:
              type: string
              default: credit_card
              enum: [credit_card, paypal, bank_transfer]
    responses:
      201:
        description: Order created successfully
      400:
        description: Empty cart or insufficient stock
      401:
        description: Unauthorized
    """
    data = request.get_json(silent=True) or {}
    err = validate_checkout(data)
    if err:
        return error_response(err, 400)

    cart_items = CartItem.query.filter_by(user_id=g.current_user.id).all()
    if not cart_items:
        return error_response("Cart is empty", 400)

    # Binding stock check before committing anything
    for item in cart_items:
        product = Product.query.get(item.product_id)
        if not product:
            return error_response(f"Product {item.product_id} no longer exists", 400)
        if product.stock_quantity < item.quantity:
            return error_response(
                f"Insufficient stock for '{product.name}'. "
                f"Available: {product.stock_quantity}, requested: {item.quantity}",
                400,
            )

    total_price = round(
        sum(i.quantity * i.product.price for i in cart_items if i.product), 2
    )

    order = Order(
        user_id=g.current_user.id,
        status="completed",
        total_price=total_price,
        payment_method=data.get("payment_method", "credit_card"),
    )
    db.session.add(order)
    db.session.flush()  # get order.id before adding items

    for item in cart_items:
        product = Product.query.get(item.product_id)
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=product.price,
        )
        db.session.add(order_item)
        product.stock_quantity -= item.quantity

    CartItem.query.filter_by(user_id=g.current_user.id).delete()

    db.session.commit()

    return success_response(order.to_dict(include_items=True), 201)


@orders_bp.route("/", methods=["GET"])
@jwt_required
def list_orders():
    """
    List the current user's orders
    ---
    tags:
      - Orders
    security:
      - Bearer: []
    parameters:
      - in: query
        name: status
        type: string
        enum: [pending, completed, cancelled]
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: per_page
        type: integer
        default: 10
    responses:
      200:
        description: Paginated order list
      401:
        description: Unauthorized
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
        if page < 1 or per_page < 1 or per_page > 100:
            return error_response("Invalid pagination parameters", 400)
    except (ValueError, TypeError):
        return error_response("page and per_page must be integers", 400)

    status = request.args.get("status", "").strip()
    query = Order.query.filter_by(user_id=g.current_user.id)

    if status:
        valid_statuses = {"pending", "completed", "cancelled"}
        if status not in valid_statuses:
            return error_response(f"Invalid status. Valid: {', '.join(valid_statuses)}", 400)
        query = query.filter_by(status=status)

    query = query.order_by(Order.created_at.desc())
    total = query.count()
    orders = query.offset((page - 1) * per_page).limit(per_page).all()

    return success_response({
        "orders": [o.to_dict() for o in orders],
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@orders_bp.route("/<int:order_id>", methods=["GET"])
@jwt_required
def get_order(order_id):
    """
    Get a single order with its items
    ---
    tags:
      - Orders
    security:
      - Bearer: []
    parameters:
      - in: path
        name: order_id
        type: integer
        required: true
    responses:
      200:
        description: Order detail with items
      401:
        description: Unauthorized
      404:
        description: Order not found or not owned by current user
    """
    order = Order.query.filter_by(
        id=order_id, user_id=g.current_user.id
    ).first()
    if not order:
        return error_response("Order not found", 404)
    return success_response(order.to_dict(include_items=True))


@orders_bp.route("/<int:order_id>/cancel", methods=["POST"])
@jwt_required
def cancel_order(order_id):
    """
    Cancel a pending order
    ---
    tags:
      - Orders
    security:
      - Bearer: []
    parameters:
      - in: path
        name: order_id
        type: integer
        required: true
    responses:
      200:
        description: Order cancelled
      400:
        description: Order cannot be cancelled (not in pending status)
      401:
        description: Unauthorized
      404:
        description: Order not found
    """
    order = Order.query.filter_by(
        id=order_id, user_id=g.current_user.id
    ).first()
    if not order:
        return error_response("Order not found", 404)
    if order.status == "cancelled":
        return error_response("Order is already cancelled", 400)

    order.status = "cancelled"
    db.session.commit()
    return success_response({"id": order.id, "status": order.status})
