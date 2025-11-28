from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
import stripe
import os
import psycopg2
import psycopg2.extras

# Local modules
from utils.db import (
    get_user_by_email,
    create_user,
    list_users,
    delete_user_by_id,
    reset_scans,
    make_admin,
    get_user_by_subscription,
    update_subscription_by_email,
)
from utils.analyzer import run_full_analysis
from utils.pdf_builder import build_pdf


# ------------------------------------------------------------
# FLASK + STRIPE SETUP
# ------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "super-secret-key")

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

DB_URL = os.environ.get("DB_URL")


# ------------------------------------------------------------
# HOME
# ------------------------------------------------------------
@app.route("/")
def index():
    return render_template("landing.html")


# ------------------------------------------------------------
# SIGNUP
# ------------------------------------------------------------
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


# ------------------------------------------------------------
# LOGIN
# ------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = get_user_by_email(email)

        if not user or user["password"] != password:
            return render_template("login.html", error="Invalid login")

        session["user_email"] = email
        return redirect("/dashboard")

    return render_template("login.html")


# ------------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------------
@app.route("/dashboard")
def dashboard():
    if "user_email" not in session:
        return redirect("/login")

    user = get_user_by_email(session["user_email"])

    subscribed = user["is_pro"]

    scans_left = max(0, 2 - user["scans_used"])
    pdf_left = 1 if not subscribed else "∞"

    return render_template(
        "dashboard.html",
        user=user,
        subscribed=subscribed,
        scans_left=scans_left,
        pdf_left=pdf_left,
    )


# ------------------------------------------------------------
# SCAN ROUTE
# ------------------------------------------------------------
@app.route("/scan", methods=["POST"])
def scan():
    if "user_email" not in session:
        return jsonify({"error": "not_logged_in"})

    user = get_user_by_email(session["user_email"])
    subscribed = user["is_pro"]

    # FREE LIMITS
    if not subscribed and user["scans_used"] >= 2:
        return jsonify({"error": "limit"})

    # Parse incoming JSON
    data = request.json
    url = data.get("url")
    keyword = data.get("keyword")
    competitor = data.get("competitor")

    # Run analyzer
    results = run_full_analysis(url, keyword, competitor)

    # Increment free scans
    if not subscribed:
        conn = psycopg2.connect(DB_URL, sslmode="require")
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET scans_used = scans_used + 1 WHERE email=%s",
            (user["email"],)
        )
        conn.commit()
        cur.close()
        conn.close()

    return jsonify(results)


# ------------------------------------------------------------
# PDF EXPORT (PRO ONLY)
# ------------------------------------------------------------
@app.route("/export-pdf", methods=["POST"])
def export_pdf():
    if "user_email" not in session:
        return jsonify({"error": "not_logged_in"}), 401

    user = get_user_by_email(session["user_email"])

    if not user["is_pro"]:
        return jsonify({"error": "not_pro"}), 403

    analysis_data = request.json

    competitor_data = analysis_data.get("competitor_data")
    filename = build_pdf(user, analysis_data, competitor_data)

    return send_file(filename, as_attachment=True)


# ------------------------------------------------------------
# PRICING PAGE
# ------------------------------------------------------------
@app.route("/pricing")
def pricing():
    return render_template("pricing.html", stripe_public_key=STRIPE_PUBLIC_KEY)


# ------------------------------------------------------------
# STRIPE CHECKOUT
# ------------------------------------------------------------
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    if "user_email" not in session:
        return jsonify({"error": "not_logged_in"}), 401

    user = get_user_by_email(session["user_email"])

    session_obj = stripe.checkout.Session.create(
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

    return jsonify({"url": session_obj.url})


@app.route("/success")
def success():
    return render_template("success.html")


@app.route("/cancel")
def cancel():
    return render_template("cancel.html")


# ------------------------------------------------------------
# STRIPE WEBHOOK
# ------------------------------------------------------------
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

    # SUBSCRIPTION COMPLETED
    if event_type == "checkout.session.completed":
        data = event["data"]["object"]

        email = data.get("customer_email")
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")

        update_subscription_by_email(
            email=email,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            status="active",
            is_pro=True,
            period_end=None
        )

    # RENEWAL / CANCEL
    elif event_type == "customer.subscription.updated":
        data = event["data"]["object"]

        subscription_id = data["id"]
        customer_id = data["customer"]
        status = data["status"]
        period_end = data["current_period_end"]

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

    return jsonify({"status": "ok"})


# ------------------------------------------------------------
# ADMIN PAGES
# ------------------------------------------------------------
@app.route("/admin/users")
def admin_users():
    users = list_users()
    return render_template("admin_users.html", users=users)


@app.route("/admin/delete/<int:user_id>")
def admin_delete_user(user_id):
    delete_user_by_id(user_id)
    return redirect("/admin/users")


@app.route("/admin/reset_scans/<int:user_id>")
def admin_reset_scans_route(user_id):
    reset_scans(user_id)
    return redirect("/admin/users")


@app.route("/admin/make_admin/<int:user_id>")
def admin_make_admin_route(user_id):
    make_admin(user_id)
    return redirect("/admin/users")


# ------------------------------------------------------------
# LOGOUT
# ------------------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ------------------------------------------------------------
# RUN LOCAL
# ------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
