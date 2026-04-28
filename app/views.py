from flask import Blueprint, render_template, redirect, url_for, session, request

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    return render_template("index.html")


@views_bp.route("/login")
def login():
    if session.get("user_id"):
        return redirect(url_for("views.index"))
    return render_template("login.html")


@views_bp.route("/register")
def register():
    if session.get("user_id"):
        return redirect(url_for("views.index"))
    return render_template("register.html")


@views_bp.route("/products/<int:product_id>")
def product_detail(product_id):
    return render_template("product_detail.html", product_id=product_id)


@views_bp.route("/cart")
def cart():
    if not session.get("user_id"):
        return redirect(url_for("views.login"))
    return render_template("cart.html")


@views_bp.route("/checkout")
def checkout():
    if not session.get("user_id"):
        return redirect(url_for("views.login"))
    return render_template("checkout.html")


@views_bp.route("/order-history")
def order_history():
    if not session.get("user_id"):
        return redirect(url_for("views.login"))
    return render_template("order_history.html")


@views_bp.route("/my-orders")
def my_orders():
    if not session.get("user_id"):
        return redirect(url_for("views.login"))
    return render_template("my_orders.html")


@views_bp.route("/orders/<int:order_id>")
def order_detail(order_id):
    if not session.get("user_id"):
        return redirect(url_for("views.login"))
    return render_template("order_detail.html", order_id=order_id)


@views_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("views.login"))
