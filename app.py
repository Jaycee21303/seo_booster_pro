from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from utils.db import get_user_by_email, update_subscription, create_user
import stripe
import os
import json

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "super-secret-key")

# Stripe keys from Render environment
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")


# -----------------------------
# HOME PAGE / LANDING
# -----------------------------
@app.route("/")
def index():
    return render_template("landing.html")


# -----------------------------
# AUTH — SIGNUP PAGE
# -----------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = get_user_by_email(email)
        if user:
            return render_template("signup.html", error="Email already exists.")

        create_user(email, password)
        return redirect("/login")

    return render_template("signup.html")


# -----------------------------
# AUTH — LOGIN PAGE
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
# CREATE CHECKOUT SESSION
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
# SUCCESS & CANCEL PAGES
# -----------------------------
@app.route("/success")
def success():
    return render_template("success.html")


@app.route("/cancel")
def cancel():
    return render_template("cancel.html")


# -----------------------------
# WEBHOOK HANDLER (CRITICAL)
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

    # -------------------------
    # EVENT: Payment Completed
    # -------------------------
    if event["type"] == "checkout.session.completed":
        data = event["data"]["object"]

        email = data.get("customer_email")
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")

        update_subscription(
            email=email,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            status="active",
            period_end=None,   # will be filled in next webhook
            is_pro=True
        )

    # -------------------------
    # EVENT: Subscription Updated (billing periods, renewals)
    # -------------------------
    if event["type"] == "customer.subscription.updated":
        data = event["data"]["object"]

        customer_id = data.get("customer")
        subscription_id = data.get("id")
        status = data.get("status")
        period_end = data["current_period_end"]

        # Get user email by subscription id
        # We added this helper inside db.py
        from utils.db import get_user_by_subscription
        user = get_user_by_subscription(subscription_id)

        if user:
            update_subscription(
                email=user["email"],
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                status=status,
                period_end=period_end,
                is_pro=(status == "active")
            )

    return jsonify({"status": "success"}), 200


# -----------------------------
# LOGOUT
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")



# -----------------------------
# RUN (Render will use gunicorn)
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
