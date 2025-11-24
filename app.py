from flask import Flask, render_template, request, redirect, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db import init_db, fetch_one, fetch_all, execute
from utils.analyzer import run_local_seo_analysis
import stripe
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "supersecret123"

# ---------------------------------------------------
# STRIPE TEST MODE (PLACEHOLDERS)
# ---------------------------------------------------
STRIPE_PUBLIC_KEY = "pk_test_yourkeyhere"
STRIPE_SECRET_KEY = "sk_test_yourkeyhere"

stripe.api_key = STRIPE_SECRET_KEY


# ---------------------------------------------------
# INIT DATABASE (SAFE – WILL NOT DELETE DATA)
# ---------------------------------------------------
def init_full_schema():
    execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE,
            password TEXT,
            scans_used INTEGER DEFAULT 0,
            pdf_downloads_used INTEGER DEFAULT 0,
            is_pro BOOLEAN DEFAULT FALSE,
            pro_expires TIMESTAMP NULL
        );
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            type TEXT,
            stripe_id TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)


init_full_schema()


# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------
def current_user():
    if "user_id" not in session:
        return None
    return fetch_one("SELECT * FROM users WHERE id=%s", (session["user_id"],))


def is_pro(user):
    if not user["is_pro"]:
        return False
    if user["pro_expires"] and user["pro_expires"] < datetime.utcnow():
        execute("UPDATE users SET is_pro=false WHERE id=%s", (user["id"],))
        return False
    return True


# ---------------------------------------------------
# LANDING PAGE
# ---------------------------------------------------
@app.route("/")
def landing():
    return render_template("landing.html")


# ---------------------------------------------------
# SIGNUP
# ---------------------------------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        existing = fetch_one("SELECT * FROM users WHERE email=%s", (email,))
        if existing:
            return render_template("signup.html", error="Email already exists.")

        hashed = generate_password_hash(password)
        execute(
            "INSERT INTO users (email, password) VALUES (%s, %s)",
            (email, hashed)
        )

        user = fetch_one("SELECT * FROM users WHERE email=%s", (email,))
        session["user_id"] = user["id"]

        return redirect("/dashboard")

    return render_template("signup.html")


# ---------------------------------------------------
# LOGIN
# ---------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = fetch_one("SELECT * FROM users WHERE email=%s", (email,))
        if not user or not check_password_hash(user["password"], password):
            return render_template("login.html", error="Invalid email or password.")

        session["user_id"] = user["id"]
        return redirect("/dashboard")

    return render_template("login.html")


# ---------------------------------------------------
# LOGOUT
# ---------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------------------------------------------
# DASHBOARD
# ---------------------------------------------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    user = current_user()
    if not user:
        return redirect("/login")

    user["is_pro"] = is_pro(user)

    limit_reached = False

    if not user["is_pro"] and user["scans_used"] >= 3:
        limit_reached = True

    keyword_score = None
    site_audit = None
    optimization_tips = None

    if request.method == "POST" and not limit_reached:
        url = request.form.get("website_url")
        keyword = request.form.get("keyword") or None

        # Run local SEO scan
        score, audit, tips = run_local_seo_analysis(url, keyword)

        keyword_score = score
        site_audit = audit
        optimization_tips = tips

        # Update scan usage
        if not user["is_pro"]:
            execute("UPDATE users SET scans_used=scans_used+1 WHERE id=%s", (user["id"],))

    # Reload user fresh from DB
    user = current_user()

    return render_template(
        "dashboard.html",
        user=user,
        limit_reached=limit_reached,
        keyword_score=keyword_score,
        site_audit=site_audit,
        optimization_tips=optimization_tips
    )


# ---------------------------------------------------
# SETTINGS
# ---------------------------------------------------
@app.route("/settings")
def settings():
    user = current_user()
    if not user:
        return redirect("/login")

    user["is_pro"] = is_pro(user)
    return render_template("settings.html", user=user)


# ---------------------------------------------------
# UPGRADE PAGE
# ---------------------------------------------------
@app.route("/upgrade")
def upgrade():
    user = current_user()
    if not user:
        return redirect("/login")
    return render_template("upgrade.html")


# ---------------------------------------------------
# BUY-SCAN PAGE
# ---------------------------------------------------
@app.route("/buy-scan")
def buy_scan():
    user = current_user()
    if not user:
        return redirect("/login")
    return render_template("buy_scan.html")


# ---------------------------------------------------
# CHECKOUT – PRO SUBSCRIPTION
# ---------------------------------------------------
@app.route("/checkout-pro")
def checkout_pro():
    user = current_user()
    if not user:
        return redirect("/login")

    session_obj = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        success_url="http://localhost:5000/pro-success",
        cancel_url="http://localhost:5000/upgrade",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": "SEO Booster Pro - Monthly"},
                "unit_amount": 499,
            },
            "quantity": 1
        }]
    )

    return redirect(session_obj.url)


# ---------------------------------------------------
# CHECKOUT – ONE-OFF SCAN
# ---------------------------------------------------
@app.route("/checkout-one")
def checkout_one():
    user = current_user()
    if not user:
        return redirect("/login")

    session_obj = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        success_url="http://localhost:5000/scan-success",
        cancel_url="http://localhost:5000/buy-scan",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": "Single SEO Scan"},
                "unit_amount": 99,
            },
            "quantity": 1
        }]
    )

    return redirect(session_obj.url)


# ---------------------------------------------------
# SUCCESS – PRO ACTIVATION
# ---------------------------------------------------
@app.route("/pro-success")
def pro_success():
    user = current_user()
    if not user:
        return redirect("/login")

    expires = datetime.utcnow() + timedelta(days=30)

    execute(
        "UPDATE users SET is_pro=true, pro_expires=%s WHERE id=%s",
        (expires, user["id"])
    )

    return redirect("/dashboard")


# ---------------------------------------------------
# SUCCESS – ONE-SCAN PURCHASE
# ---------------------------------------------------
@app.route("/scan-success")
def scan_success():
    user = current_user()
    if not user:
        return redirect("/login")

    execute(
        "UPDATE users SET scans_used=scans_used-1 WHERE id=%s",
        (user["id"],)
    )

    return redirect("/dashboard")


# ---------------------------------------------------
# STRIPE WEBHOOK PLACEHOLDER
# ---------------------------------------------------
@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    print("Stripe webhook received")
    return "ok", 200


# ---------------------------------------------------
# RUN SERVER
# ---------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
