from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import stripe
from config import STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY, STRIPE_PRICE_ID, WEBHOOK_SECRET

app = Flask(__name__)
app.secret_key = "super-secret-key"

# Stripe setup
stripe.api_key = STRIPE_SECRET_KEY


# -----------------------------
# HOME / LANDING PAGE
# -----------------------------
@app.route("/")
def index():
    return render_template("landing.html")


# -----------------------------
# PRICING PAGE (UPGRADE PAGE)
# -----------------------------
@app.route("/pricing")
def pricing():
    return render_template("pricing.html", stripe_public_key=STRIPE_PUBLIC_KEY)


# -----------------------------
# CREATE CHECKOUT SESSION
# (Redirects user to Stripe checkout)
# -----------------------------
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price": STRIPE_PRICE_ID,
                "quantity": 1
            }],
            allow_promotion_codes=True,
            success_url=url_for("success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("cancel", _external=True),
        )
        return jsonify({"url": checkout_session.url})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# -----------------------------
# SUCCESS PAGE
# (User comes here after Stripe payment)
# -----------------------------
@app.route("/success")
def success():
    # Let user into the dashboard immediately
    session["subscribed"] = True
    return render_template("success.html")


# -----------------------------
# CANCEL PAGE (User canceled checkout)
# -----------------------------
@app.route("/cancel")
def cancel():
    return render_template("cancel.html")


# -----------------------------
# WEBHOOK HANDLER
# Stripe → your server
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
        return f"Webhook Error: {e}", 400

    # Subscription activated
    if event["type"] == "checkout.session.completed":
        print("✅ Subscription activated by Stripe webhook")

    # Subscription renewed
    if event["type"] == "invoice.payment_succeeded":
        print("💰 Subscription renewed")

    # Subscription canceled
    if event["type"] == "customer.subscription.deleted":
        print("❌ Subscription canceled")
        session["subscribed"] = False

    return "", 200


# -----------------------------
# ACCESS CONTROL DECORATOR
# (Protect pages behind subscription)
# -----------------------------
def require_subscription(f):
    def wrapper(*args, **kwargs):
        if not session.get("subscribed"):
            return redirect("/pricing")
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


# -----------------------------
# PROTECTED DASHBOARD
# -----------------------------
@app.route("/dashboard")
@require_subscription
def dashboard():
    return render_template("dashboard.html")


# -----------------------------
# START SERVER (LOCAL DEV)
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
