from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
import stripe
import os
import json

from utils.db import (
    get_user_by_email,
    create_user,
    get_user_by_subscription,
    update_subscription_by_email,
    list_users,
    delete_user_by_id,
    reset_scans,
    make_admin,
)

from utils.analyzer import run_local_seo_analysis
from utils.pdf_builder import build_pdf

import psycopg2
import io


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "super-secret-key")

# Stripe keys
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")


# ===============================================================
# HOME
# ===============================================================
@app.route("/")
def index():
    return render_template("landing.html")


# ===============================================================
# SIGNUP
# ===============================================================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if get_user_by_email(email):
            return render_template("signup.html", error="Email already exists.")

        create_user(email, password)
        return redirect("/login")

    return render_template("signup.html")


# ===============================================================
# LOGIN
# ===============================================================
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


# ===============================================================
# DASHBOARD
# ===============================================================
@app.route("/dashboard")
def dashboard():
    if "user_email" not in session:
        return redirect("/login")

    user = get_user_by_email(session["user_email"])

    subscribed = user["is_pro"]
    scans_left = max(0, 2 - user["scans_used"]) if not subscribed else None
    pdf_left = 1 if not subscribed else None

    return render_template(
        "dashboard.html",
        user=user,
        subscribed=subscribed,
        scans_left=scans_left,
        pdf_left=pdf_left
    )


# ===============================================================
# STRIPE CHECKOUT
# ===============================================================
@app.route("/pricing")
def pricing():
    return render_template("pricing.html", stripe_public_key=STRIPE_PUBLIC_KEY)


@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    if "user_email" not in session:
        return jsonify({"error": "Not logged in"}), 401

    try:
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=session["user_email"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            success_url=request.host_url + "success",
            cancel_url=request.host_url + "cancel",
        )

        return jsonify({"url": checkout_session.url})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/success")
def success():
    return render_template("success.html")


@app.route("/cancel")
def cancel():
    return render_template("cancel.html")


# ===============================================================
# STRIPE WEBHOOK
# ===============================================================
@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    event_type = event["type"]

    # Payment completed
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
                period_end=None,
            )

    # Subscription updated
    elif event_type == "customer.subscription.updated":
        data = event["data"]["object"]
        sub_id = data.get("id")
        customer_id = data.get("customer")
        status = data.get("status")
        period_end = data.get("current_period_end")

        user = get_user_by_subscription(sub_id)
        if user:
            update_subscription_by_email(
                email=user["email"],
                stripe_customer_id=customer_id,
                stripe_subscription_id=sub_id,
                status=status,
                is_pro=(status == "active"),
                period_end=period_end,
            )

    return jsonify({"status": "success"}), 200


# ===============================================================
# LOGOUT
# ===============================================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ===============================================================
# ANALYZER /scan
# ===============================================================
@app.route("/scan", methods=["POST"])
def scan():
    if "user_email" not in session:
        return jsonify({"error": "not_logged_in"})

    data = request.get_json()
    url = data.get("url")
    keyword = data.get("keyword")
    competitor_url = data.get("competitor")

    user = get_user_by_email(session["user_email"])

    # Free limit enforcement
    if not user["is_pro"]:
        if user["scans_used"] >= 2:
            return jsonify({"error": "limit"})
        conn = psycopg2.connect(os.environ["DB_URL"], sslmode="require")
        cur = conn.cursor()
        cur.execute("UPDATE users SET scans_used = scans_used + 1 WHERE email = %s", (user["email"],))
        conn.commit()
        cur.close()
        conn.close()

    # Main scan
    (
        main_score,
        audit,
        tips,
        content,
        tech,
        keyword_score,
        onpage,
        links,
        page_meta,
    ) = run_local_seo_analysis(url, keyword)

    result = {
        "score": main_score,
        "audit": audit,
        "tips": tips,
        "content": content,
        "technical": tech,
        "keyword": keyword_score,
        "onpage": onpage,
        "links": links,
        "page_meta": page_meta,
    }

    # Competitor scan (Pro only)
    if competitor_url and user["is_pro"]:
        (
            c_score,
            c_audit,
            c_tips,
            c_content,
            c_tech,
            c_keyword,
            c_onpage,
            c_links,
            _
        ) = run_local_seo_analysis(competitor_url, keyword)

        result["competitor_data"] = {
            "content": c_content,
            "technical": c_tech,
            "keyword": c_keyword,
            "onpage": c_onpage,
            "links": c_links,
            "score": c_score
        }
    else:
        result["competitor_data"] = None

    return jsonify(result)


# ===============================================================
# NEW → WORKING /export-pdf POST ROUTE
# ===============================================================
@app.route("/export-pdf", methods=["POST"])
def export_pdf():
    if "user_email" not in session:
        return "Not logged in", 403

    user = get_user_by_email(session["user_email"])
    if not user["is_pro"]:
        return "Upgrade Required", 403

    data = request.get_json()

    analysis_data = {
        "score": data.get("score", 0),
        "audit": data.get("audit", ""),
        "tips": data.get("tips", ""),
        "content": data.get("content", 0),
        "technical": data.get("technical", 0),
        "keyword": data.get("keyword", 0),
        "onpage": data.get("onpage", 0),
        "links": data.get("links", 0),
    }

    competitor_data = data.get("competitor_data")

    try:
        pdf_bytes = build_pdf(
            user_data=user,
            analysis_data=analysis_data,
            competitor_data=competitor_data
        )
    except Exception as e:
        print("PDF ERROR:", e)
        return "PDF generation error", 500

    buffer = io.BytesIO(pdf_bytes)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="seo_report.pdf"
    )


# ===============================================================
# OLD GET /pdf (still here – untouched)
# ===============================================================
@app.route("/pdf")
def pdf_download():
    if "user_email" not in session:
        return "Not logged in", 403

    user = get_user_by_email(session["user_email"])
    if not user["is_pro"]:
        return "Upgrade required", 403

    url = request.args.get("url")
    keyword = request.args.get("keyword")
    competitor = request.args.get("competitor")

    if not url:
        return "Missing URL", 400

    (
        score,
        audit,
        tips,
        content,
        tech,
        keyword_score,
        onpage,
        links,
        _
    ) = run_local_seo_analysis(url, keyword)

    analysis_data = {
        "score": score,
        "audit": audit,
        "tips": tips,
        "content": content,
        "technical": tech,
        "keyword": keyword_score,
        "onpage": onpage,
        "links": links
    }

    competitor_data = None
    if competitor:
        (
            c_score,
            c_audit,
            c_tips,
            c_content,
            c_tech,
            c_keyword,
            c_onpage,
            c_links,
            _
        ) = run_local_seo_analysis(competitor, keyword)

        competitor_data = {
            "score": c_score,
            "audit": c_audit,
            "tips": c_tips,
            "content": c_content,
            "technical": c_tech,
            "keyword": c_keyword,
            "onpage": c_onpage,
            "links": c_links
        }

    pdf_bytes = build_pdf(
        user_data=user,
        analysis_data=analysis_data,
        competitor_data=competitor_data
    )

    buffer = io.BytesIO(pdf_bytes)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="seo_report.pdf"
    )


# ===============================================================
# ADMIN ROUTES
# ===============================================================
@app.route("/admin/users")
def admin_users():
    users = list_users()
    return render_template("admin_users.html", users=users)


@app.route("/admin/delete/<int:user_id>")
def admin_delete_user(user_id):
    delete_user_by_id(user_id)
    return redirect("/admin/users")


@app.route("/admin/reset_scans/<int:user_id>")
def admin_reset_scans(user_id):
    reset_scans(user_id)
    return redirect("/admin/users")


@app.route("/admin/make_admin/<int:user_id>")
def admin_make_admin_route(user_id):
    make_admin(user_id)
    return redirect("/admin/users")


# ===============================================================
# RUN LOCAL
# ===============================================================
if __name__ == "__main__":
    app.run(debug=True)
