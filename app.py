from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import stripe
from config import STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY, STRIPE_PRICE_ID, WEBHOOK_SECRET

app = Flask(__name__)
app.secret_key = "super-secret-key"

# Stripe setup
stripe.api_key = STRIPE_SECRET_KEY


# ====================================================
# HOME / LANDING PAGE
# ====================================================
@app.route("/")
def index():
    return render_template("landing.html")


# ====================================================
# LOGIN
# ====================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # Simple fake login (remove later when DB added)
        if email and password:
            session["user"] = email
            return redirect("/dashboard")

        return render_template("login.html", error="Invalid login")

    return render_template("login.html")


# ====================================================
# SIGNUP
# ====================================================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # Simple fake signup (remove later when DB added)
        if email and password:
            session["user"] = email
            return redirect("/pricing")

        return render_template("signup.html", error="Signup failed")

    return render_template("signup.html")


# ====================================================
# PRICING PAGE
# ====================================================
@app.route("/pricing")
def pricing():
    return render_template("pricing.html", stripe_public_key=STRIPE_PUBLIC_KEY)


# ====================================================
# CREATE CHECKOUT SESSION
# ====================================================
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            }],
            allow_promotion_codes=True,
            success_url=url_for("success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("cancel", _external=True),
        )
        return jsonify({"url": checkout_session.url})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ====================================================
# SUCCESS / CANCEL
# ====================================================
@app.route("/success")
def success():
    session["subscribed"] = True
    return render_template("success.html")


@app.route("/cancel")
def cancel():
    return render_template("cancel.html")


# ====================================================
# STRIPE WEBHOOK
# ====================================================
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
        print("✅ Subscription activated")

    # Subscription renewed
    if event["type"] == "invoice.payment_succeeded":
        print("💰 Subscription renewed")

    # Subscription canceled
    if event["type"] == "customer.subscription.deleted":
        print("❌ Subscription canceled")
        session["subscribed"] = False

    return "", 200


# ====================================================
# SUBSCRIPTION GUARD
# ====================================================
def require_subscription(f):
    def wrapper(*args, **kwargs):
        if not session.get("subscribed"):
            return redirect("/pricing")
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


# ====================================================
# DASHBOARD (PROTECTED)
# ====================================================
@app.route("/dashboard")
@require_subscription
def dashboard():
    if not session.get("user"):
        return redirect("/login")

    return render_template("dashboard.html")


# ====================================================
# RUN LOCAL
# ====================================================
if __name__ == "__main__":
    app.run(debug=True)
