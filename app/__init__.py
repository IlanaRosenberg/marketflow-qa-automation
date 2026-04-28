from flask import Flask
from flasgger import Swagger
from .config import config_map
from .database import db


def create_app(env="development"):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_map[env])

    db.init_app(app)

    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/api/openapi.json",
                "rule_filter": lambda rule: rule.rule.startswith("/api/"),
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api/docs",
    }
    swagger_template = {
        "info": {
            "title": "MarketFlow API",
            "description": "Mini marketplace REST API for QA Automation practice",
            "version": "1.0.0",
        },
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT token: Bearer <token>",
            }
        },
    }
    Swagger(app, config=swagger_config, template=swagger_template)

    from .auth.routes import auth_bp
    from .products.routes import products_bp
    from .cart.routes import cart_bp
    from .orders.routes import orders_bp
    from .views import views_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(views_bp)

    with app.app_context():
        db.create_all()

    return app
