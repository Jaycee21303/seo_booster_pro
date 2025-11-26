import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import stripe
from config import STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY, STRIPE_PRICE_ID, WEBHOOK_SECRET

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret")

# Stripe setup
stripe.api_key = STRIPE_SECRET_KEY


# -----------------------------
# USER SESSION HELPERS
# -----------------------------
def current_user():
    return session.get("user")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -----------------------------
# HOME / PAGES
# -----------------------------
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


# -----------------------------
# LOGIN / SIGNUP TEMP MOCK
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        session["user"] = {"email": email, "is_pro": False}
        return redirect("/dashboard")
    return render_template("login.html")


# -----------------------------
# SUCCESS / CANCEL PAGES
# -----------------------------
@app.route("/success")
def success():
    return render_template("success.html")


@app.route("/cancel")
def cancel():
    return render_template("cancel.html")


# -----------------------------
# 🔥 CREATE CHECKOUT SESSION (FIXED!)
# -----------------------------
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    user = current_user()
    if not user:
        return jsonify({"error": "auth"}), 401

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=user["email"],
            line_items=[{
                "price": STRIPE_PRICE_ID,
                "quantity": 1
            }],
            success_url=url_for('success', _external=True),
            cancel_url=url_for('cancel', _external=True)
        )

        # RETURN checkout_session.url (REQUIRED)
        return jsonify({"url": checkout_session.url})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# -----------------------------
# 🔥 STRIPE WEBHOOK HANDLER
# -----------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except Exception as e:
        return "Webhook error: " + str(e), 400

    # Successful subscription
    if event["type"] == "checkout.session.completed":
        session_obj = event["data"]["object"]
        customer_email = session_obj.get("customer_email")

        # Mark user as PRO (mock DB)
        if "user" in session and session["user"]["email"] == customer_email:
            session["user"]["is_pro"] = True

    return "OK", 200


# -----------------------------
# START SERVER
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
