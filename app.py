import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import stripe

# DB helpers
from utils.db import (
    get_user_by_email,
    create_user_if_not_exists,
    mark_user_pro,
    update_stripe_ids
)

from config import STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY, STRIPE_PRICE_ID, WEBHOOK_SECRET

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret")

# Stripe
stripe.api_key = STRIPE_SECRET_KEY


# ----------------------------------------------------
# USER SESSION HELPERS
# ----------------------------------------------------
def current_user():
    email = session.get("email")
    if not email:
        return None
    return get_user_by_email(email)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ----------------------------------------------------
# PAGES
# ----------------------------------------------------
@app.route("/")
def index():
    return render_template("landing.html")


@app.route("/pricing")
def pricing():
    return render_template("pricing.html", stripe_public_key=STRIPE_PUBLIC_KEY)


@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect("/login")
    return render_template("dashboard.html", user=user)


# ----------------------------------------------------
# LOGIN / SIGNUP  (REAL DB)
# ----------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")

        # Make sure user exists in DB
        create_user_if_not_exists(email)

        # Store in session
        session["email"] = email
        return redirect("/dashboard")

    return render_template("login.html")


# ----------------------------------------------------
# SUCCESS / CANCEL
# ----------------------------------------------------
@app.route("/success")
def success():
    return render_template("success.html")


@app.route("/cancel")
def cancel():
    return render_template("cancel.html")


# ----------------------------------------------------
# 🔥 CREATE CHECKOUT SESSION (REAL DB)
# ----------------------------------------------------
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    user = current_user()
    if not user:
        return jsonify({"error": "not_logged_in"}), 401

    try:
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            customer_email=user["email"],
            line_items=[{
                "price": STRIPE_PRICE_ID,
                "quantity": 1
            }],
            success_url=url_for("success", _external=True),
            cancel_url=url_for("cancel", _external=True)
        )

        return jsonify({"url": checkout_session.url})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ----------------------------------------------------
# 🔥 STRIPE WEBHOOK (FULL DB INTEGRATION)
# ----------------------------------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except Exception as e:
        return f"Webhook Error: {e}", 400

    # ------------------------------------------------
    # EVENT 1: checkout.session.completed
    # ------------------------------------------------
    if event["type"] == "checkout.session.completed":
        session_obj = event["data"]["object"]

        email = session_obj.get("customer_email")
        stripe_customer = session_obj.get("customer")
        stripe_subscription = session_obj.get("subscription")

        # Update DB
        user = get_user_by_email(email)
        if user:
            update_stripe_ids(email, stripe_customer, stripe_subscription)
            mark_user_pro(email)

    # ------------------------------------------------
    # EVENT 2: customer.subscription.deleted  (optional)
    # ------------------------------------------------
    if event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        stripe_customer = subscription.get("customer")

        # optional: Lookup user by stripe customer id and downgrade

    return "OK", 200


# ----------------------------------------------------
# START
# ----------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
