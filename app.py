from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from utils.db import (
    get_user_by_email,
    create_user,
    get_user_by_subscription,
    update_subscription_by_email,
    list_users,
    delete_user_by_id,
    reset_scans,
    make_admin,
    create_admin,
    update_user
)
import stripe
import os
import json
import psycopg2

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "super-secret-key")

# Stripe setup
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")


# ============================================================
# ADMIN SECURITY CHECK
# ============================================================
def require_admin():
    if "user_email" not in session:
        return False

    user = get_user_by_email(session["user_email"])
    return user and user.get("is_admin") == True


# ============================================================
# TEMPORARY ADMIN RESET (REMOVE AFTER LOGIN)
# ============================================================
@app.route("/reset-admin")
def reset_admin_route():
    create_admin()
    return "Admin reset. Login with admin@admin.com / admin123"


# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def index():
    return render_template("landing.html")


# -----------------------------
# SIGNUP
# -----------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if get_user_by_email(email):
            return render_template("signup.html", error="Email already exists")

        create_user(email, password)
        return redirect("/login")

    return render_template("signup.html")


# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = get_user_by_email(email)

        if not user or user["password"] != password:
            return render_template("login.html", error="Invalid login.")

        session["user_email"] = email
        return redirect("/dashboard")

    return render_template("login.html")


# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/dashboard")
def dashboard():
    if "user_email" not in session:
        return redirect("/login")

    user = get_user_by_email(session["user_email"])
    return render_template("dashboard.html", user=user)


# -----------------------------
# PRICING PAGE
# -----------------------------
@app.route("/pricing")
def pricing():
    return render_template("pricing.html", stripe_public_key=STRIPE_PUBLIC_KEY)


# -----------------------------
# STRIPE CHECKOUT
# -----------------------------
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    if "user_email" not in session:
        return jsonify({"error": "Not logged in"}), 401

    user = get_user_by_email(session["user_email"])

    try:
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{
                "price": STRIPE_PRICE_ID,
                "quantity": 1
            }],
            customer_email=user["email"],
            success_url=request.host_url + "success",
            cancel_url=request.host_url + "cancel",
        )

        return jsonify({"url": checkout_session.url})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# -----------------------------
# SUCCESS / CANCEL
# -----------------------------
@app.route("/success")
def success():
    return render_template("success.html")


@app.route("/cancel")
def cancel():
    return render_template("cancel.html")


# -----------------------------
# STRIPE WEBHOOK
# -----------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    event_type = event["type"]

    if event_type == "checkout.session.completed":
        data = event["data"]["object"]

        email = data.get("customer_email")
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")

        if email:
            update_subscription_by_email(
                email=email,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                status="active",
                is_pro=True,
                period_end=None
            )

    elif event_type == "customer.subscription.updated":
        data = event["data"]["object"]

        subscription_id = data.get("id")
        customer_id = data.get("customer")
        status = data.get("status")
        period_end = data.get("current_period_end")

        user = get_user_by_subscription(subscription_id)

        if user:
            update_subscription_by_email(
                email=user["email"],
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                status=status,
                is_pro=(status == "active"),
                period_end=period_end
            )

    return jsonify({"status": "success"}), 200


# -----------------------------
# LOGOUT
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =============================================================
# ADMIN PAGES (ALL PROTECTED)
# =============================================================

@app.route("/admin/users")
def admin_users_page():
    if not require_admin():
        return redirect("/login")

    users = list_users()
    return render_template("admin_users.html", users=users)


@app.route("/admin/delete/<int:user_id>")
def admin_delete_user(user_id):
    if not require_admin():
        return redirect("/login")

    delete_user_by_id(user_id)
    return redirect("/admin/users")


@app.route("/admin/reset_scans/<int:user_id>")
def admin_reset_scans_route(user_id):
    if not require_admin():
        return redirect("/login")

    reset_scans(user_id)
    return redirect("/admin/users")


@app.route("/admin/make_admin/<int:user_id>")
def admin_make_admin_route(user_id):
    if not require_admin():
        return redirect("/login")

    make_admin(user_id)
    return redirect("/admin/users")


# -------------------------------------------------------------
# EDIT USER (MODAL UPDATE)
# -------------------------------------------------------------
@app.route("/admin/update/<int:user_id>", methods=["POST"])
def admin_update_user(user_id):
    if not require_admin():
        return redirect("/login")

    email = request.form.get("email")
    password = request.form.get("password")
    is_pro = request.form.get("is_pro") == "on"
    is_admin_flag = request.form.get("is_admin") == "on"

    if password.strip() == "":
        password = None

    update_user(
        user_id=user_id,
        email=email,
        is_pro=is_pro,
        is_admin=is_admin_flag,
        password=password
    )

    return redirect("/admin/users")


# -------------------------------------------------------------
# ONE-TIME DATABASE FIX ROUTE (ADMIN ONLY)
# -------------------------------------------------------------
@app.route("/admin-fix-db")
def admin_fix_db():
    if not require_admin():
        return redirect("/login")

    conn = psycopg2.connect(os.environ["DB_URL"], sslmode="require")
    cur = conn.cursor()

    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS scans_used INTEGER DEFAULT 0;")

    conn.commit()
    cur.close()
    conn.close()

    return "Database patched successfully!"


# -----------------------------
# RUN LOCAL
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)

