from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import stripe
from config import STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY, STRIPE_PRICE_ID, WEBHOOK_SECRET

app = Flask(__name__)
app.secret_key = "super-secret-key"

stripe.api_key = STRIPE_SECRET_KEY


# -------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------
def get_scan_count():
    return session.get("scan_count", 0)


def increment_scan_count():
    session["scan_count"] = get_scan_count() + 1


def run_full_scan(url, keyword=None, competitor=None):
    """
    REAL JSON STRUCTURE that matches the dashboard.js AJAX EXACTLY.
    """
    return {
        "score": 87,
        "content": 78,
        "keyword": 72,
        "technical": 90,
        "onpage": 65,
        "links": 54,

        "audit": (
            "• Improve page speed.\n"
            "• Add missing alt tags.\n"
            "• Use structured data.\n"
            "• Fix missing meta descriptions."
        ),

        "tips": (
            "• Improve internal linking.\n"
            "• Increase keyword density.\n"
            "• Add H2/H3 headings.\n"
            "• Add sitemap.xml."
        ),

        "limit_reached": False
    }


# -------------------------------------------------------------------
# STATIC ROUTES
# -------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("landing.html")


@app.route("/dashboard")
def dashboard():
    if not session.get("user"):
        return redirect("/login")

    subscribed = session.get("subscribed", False)
    scan_count = session.get("scan_count", 0)

    scans_left = None
    if not subscribed:
        scans_left = max(0, 3 - scan_count)

    return render_template(
        "dashboard.html",
        subscribed=subscribed,
        scans_left=scans_left
    )


@app.route("/settings")
def settings():
    if not session.get("user"):
        return redirect("/login")
    return render_template("settings.html")


# -------------------------------------------------------------------
# AUTH ROUTES
# -------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email and password:
            session["user"] = email
            return redirect("/dashboard")

        return render_template("login.html", error="Invalid login")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email and password:
            session["user"] = email
            session["subscribed"] = False
            session["scan_count"] = 0
            return redirect("/dashboard")

        return render_template("signup.html", error="Signup failed")

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -------------------------------------------------------------------
# STRIPE / BILLING
# -------------------------------------------------------------------
@app.route("/pricing")
def pricing():
    return render_template("pricing.html", stripe_public_key=STRIPE_PUBLIC_KEY)


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


@app.route("/success")
def success():
    session["subscribed"] = True
    return render_template("success.html")


@app.route("/cancel")
def cancel():
    return render_template("cancel.html")


@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except Exception as e:
        return f"Webhook Error: {e}", 400

    if event["type"] == "checkout.session.completed":
        print("🔥 Subscription started")

    if event["type"] == "invoice.payment_succeeded":
        print("💰 Subscription renewed")

    if event["type"] == "customer.subscription.deleted":
        print("❌ Subscription canceled")
        session["subscribed"] = False

    return "", 200


# -------------------------------------------------------------------
# AJAX / SCAN ENDPOINT
# -------------------------------------------------------------------
@app.route("/scan", methods=["POST"])
def scan():
    if not session.get("user"):
        return jsonify({"error": "auth", "message": "Login required"}), 403

    data = request.get_json()

    url = data.get("url")
    keyword = data.get("keyword")
    competitor = data.get("competitor")

    if not url:
        return jsonify({"error": "invalid", "message": "URL required"}), 400

    # PRO USERS → unlimited scans
    if session.get("subscribed"):
        return jsonify(run_full_scan(url, keyword, competitor))

    # FREE USERS → max 3 scans
    current = session.get("scan_count", 0)

    if current >= 3:
        return jsonify({
            "error": "limit",
            "message": "All 3 free scans used",
            "limit_reached": True
        }), 403

    increment_scan_count()
    return jsonify(run_full_scan(url, keyword, competitor))


# -------------------------------------------------------------------
# LAUNCH
# -------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
