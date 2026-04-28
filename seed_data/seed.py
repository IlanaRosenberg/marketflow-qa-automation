import json
import os
from werkzeug.security import generate_password_hash


def seed_db():
    from app.database import db
    from app.models import User, Product

    base_dir = os.path.dirname(__file__)

    with open(os.path.join(base_dir, "users.json")) as f:
        users_data = json.load(f)

    for u in users_data:
        if not User.query.filter_by(email=u["email"]).first():
            user = User(
                username=u["username"],
                email=u["email"],
                password_hash=generate_password_hash(u["password"]),
                first_name=u.get("first_name"),
                last_name=u.get("last_name"),
            )
            db.session.add(user)

    with open(os.path.join(base_dir, "products.json")) as f:
        products_data = json.load(f)

    for p in products_data:
        if not Product.query.filter_by(sku=p["sku"]).first():
            product = Product(
                id=p["id"],
                name=p["name"],
                description=p.get("description"),
                price=p["price"],
                stock_quantity=p["stock_quantity"],
                sku=p["sku"],
                category=p.get("category"),
                image_url=p.get("image_url"),
            )
            db.session.add(product)

    db.session.commit()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from app import create_app
    flask_app = create_app("development")
    with flask_app.app_context():
        seed_db()
    print("Seed data loaded successfully.")
