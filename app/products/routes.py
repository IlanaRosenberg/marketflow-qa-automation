from flask import Blueprint, request
from app.database import db
from app.models import Product
from app.utils import success_response, error_response
from app.auth.decorators import jwt_required
from app.products.schemas import validate_create_product

products_bp = Blueprint("products", __name__, url_prefix="/api/products")


@products_bp.route("/", methods=["GET"])
def list_products():
    """
    List all products with optional filtering and pagination
    ---
    tags:
      - Products
    parameters:
      - in: query
        name: search
        type: string
        description: Search by name or description
      - in: query
        name: category
        type: string
        description: Filter by category
      - in: query
        name: sort
        type: string
        enum: [name, price, -price]
        description: Sort field (prefix - for descending)
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
        description: Paginated product list
      400:
        description: Invalid pagination parameters
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
        if page < 1 or per_page < 1 or per_page > 100:
            return error_response("Invalid pagination parameters", 400)
    except (ValueError, TypeError):
        return error_response("page and per_page must be integers", 400)

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    sort = request.args.get("sort", "name")

    query = Product.query

    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%"),
            )
        )
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))

    sort_map = {
        "name": Product.name.asc(),
        "price": Product.price.asc(),
        "-price": Product.price.desc(),
    }
    query = query.order_by(sort_map.get(sort, Product.name.asc()))

    total = query.count()
    products = query.offset((page - 1) * per_page).limit(per_page).all()

    return success_response({
        "products": [p.to_dict() for p in products],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    })


@products_bp.route("/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """
    Get a single product by ID
    ---
    tags:
      - Products
    parameters:
      - in: path
        name: product_id
        type: integer
        required: true
    responses:
      200:
        description: Product details
      404:
        description: Product not found
    """
    product = Product.query.get(product_id)
    if not product:
        return error_response("Product not found", 404)
    return success_response(product.to_dict())


@products_bp.route("/", methods=["POST"])
@jwt_required
def create_product():
    """
    Create a new product (authenticated)
    ---
    tags:
      - Products
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [name, price, stock_quantity, sku]
          properties:
            name:
              type: string
            description:
              type: string
            price:
              type: number
            stock_quantity:
              type: integer
            sku:
              type: string
            category:
              type: string
            image_url:
              type: string
    responses:
      201:
        description: Product created
      400:
        description: Validation error or duplicate SKU
      401:
        description: Unauthorized
    """
    data = request.get_json(silent=True)
    err = validate_create_product(data)
    if err:
        return error_response(err, 400)

    sku = data["sku"].strip()
    if Product.query.filter_by(sku=sku).first():
        return error_response("SKU already exists", 400)

    product = Product(
        name=data["name"].strip(),
        description=(data.get("description") or "").strip() or None,
        price=round(float(data["price"]), 2),
        stock_quantity=int(data["stock_quantity"]),
        sku=sku,
        category=(data.get("category") or "").strip() or None,
        image_url=(data.get("image_url") or "").strip() or None,
    )
    db.session.add(product)
    db.session.commit()

    return success_response(product.to_dict(), 201)
