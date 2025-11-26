import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db import fetch_one, fetch_all, execute

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecret")

FREE_SCAN_LIMIT = 2          # free scans per month
FREE_PDF_LIMIT = 1           # free pdfs per month


# ============================================================
# AUTO-CREATE ADMIN
# ============================================================

def ensure_admin_exists():
    execute("""
        INSERT INTO users (id, email, password, is_pro, is_admin, scans_used, pdf_used, last_reset)
        VALUES (1, 'admin@admin.com', %s, TRUE, TRUE, 0, 0, CURRENT_DATE)
        ON CONFLICT (id)
        DO UPDATE SET
            email = EXCLUDED.email,
            password = EXCLUDED.password,
            is_admin = TRUE;
    """, (generate_password_hash("M4ry321!"),))
    print("✓ Admin ensured")


ensure_admin_exists()


# ============================================================
# MONTHLY RESET FUNCTION
# ============================================================

def reset_monthly_if_needed(user_id):
    """Resets scans_used and pdf_used on 1st of month."""
    row = fetch_one("SELECT last_reset FROM users WHERE id=%s", (user_id,))
    if not row:
        return

    last = row["last_reset"]
    today = datetime.utcnow().date()

    # If first day of month OR month changed
    if last is None or (last.month != today.month or last.year != today.year):
        execute("""
            UPDATE users
            SET scans_used = 0,
                pdf_used = 0,
                last_reset = %s
            WHERE id=%s
        """, (today, user_id))
        print(f"✓ Monthly reset for user {user_id}")


# ============================================================
# SESSION HELPERS
# ============================================================

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return fetch_one("SELECT * FROM users WHERE id=%s", (uid,))


# ============================================================
# AUTH ROUTES
# ============================================================

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        hashed = generate_password_hash(password)

        execute("""
            INSERT INTO users (email, password)
            VALUES (%s, %s)
        """, (email, hashed))

        user = fetch_one("SELECT * FROM users WHERE email=%s", (email,))
        session["user_id"] = user["id"]

        return redirect("/dashboard")

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = fetch_one("SELECT * FROM users WHERE email=%s", (email,))
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            return redirect("/dashboard")

        return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ============================================================
# DASHBOARD ROUTE
# ============================================================

@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect("/login")

    reset_monthly_if_needed(user["id"])

    subscribed = user["is_pro"]
    scans_used = user["scans_used"]
    pdf_used = user.get("pdf_used", 0)

    scans_left = max(0, FREE_SCAN_LIMIT - scans_used) if not subscribed else None
    pdf_left = max(0, FREE_PDF_LIMIT - pdf_used) if not subscribed else None

    return render_template(
        "dashboard.html",
        user=user,
        subscribed=subscribed,
        scans_left=scans_left,
        pdf_left=pdf_left
    )


# ============================================================
# SCAN ENGINE
# ============================================================

@app.route("/scan", methods=["POST"])
def scan():
    user = current_user()
    if not user:
        return jsonify({"error": "auth"}), 401

    reset_monthly_if_needed(user["id"])

    subscribed = user["is_pro"]

    # FREE PLAN ENFORCEMENT
    if not subscribed:
        if user["scans_used"] >= FREE_SCAN_LIMIT:
            return jsonify({"error": "limit"}), 403

        execute("""
            UPDATE users SET scans_used = scans_used + 1
            WHERE id = %s
        """, (user["id"],))

    # FAKE PLACEHOLDER ANALYSIS (works with your UI)
    score = 74
    content = 66
    keyword_score = 61
    technical = 79
    onpage = 72
    links = 69

    audit = "Your site audit goes here..."
    tips = "Optimization tips go here..."

    data = request.json
    competitor = data.get("competitor", "")

    competitor_data = None
    competitor_summary = ""
    competitor_advantages = ""
    competitor_disadvantages = ""

    if competitor:
        competitor_data = {
            "content": 52,
            "keyword": 59,
            "technical": 55,
            "onpage": 62,
            "links": 47
        }
        competitor_summary = "Competitor summary..."
        competitor_advantages = "Where the competitor is stronger..."
        competitor_disadvantages = "Where you outperform competitor..."

    return jsonify({
        "score": score,
        "content": content,
        "keyword": keyword_score,
        "technical": technical,
        "onpage": onpage,
        "links": links,
        "audit": audit,
        "tips": tips,
        "competitor_data": competitor_data,
        "competitor_summary": competitor_summary,
        "competitor_advantages": competitor_advantages,
        "competitor_disadvantages": competitor_disadvantages
    })


# ============================================================
# PRICING (YOUR CUSTOM PAGE, NO CHANGES)
# ============================================================

@app.route("/pricing")
def pricing():
    return render_template("pricing.html")


# ============================================================
# ADMIN
# ============================================================

@app.route("/admin/users")
def admin_users():
    user = current_user()
    if not user or not user["is_admin"]:
        return "Access Denied"

    users = fetch_all("SELECT * FROM users ORDER BY id ASC")
    return render_template("admin_users.html", users=users)


@app.route("/admin/reset_scans/<int:uid>")
def admin_reset_scans(uid):
    user = current_user()
    if not user or not user["is_admin"]:
        return "Access Denied"

    execute("UPDATE users SET scans_used=0, pdf_used=0 WHERE id=%s", (uid,))
    return redirect("/admin/users")


@app.route("/admin/edit/<int:uid>", methods=["GET", "POST"])
def admin_edit(uid):
    user = current_user()
    if not user or not user["is_admin"]:
        return "Access Denied"

    row = fetch_one("SELECT * FROM users WHERE id=%s", (uid,))
    if not row:
        return "User not found"

    if request.method == "POST":
        email = request.form["email"]
        is_pro = request.form.get("is_pro") == "on"
        is_admin = request.form.get("is_admin") == "on"

        execute("""
            UPDATE users SET email=%s, is_pro=%s, is_admin=%s
            WHERE id=%s
        """, (email, is_pro, is_admin, uid))

        return redirect("/admin/users")

    return render_template("admin_edit_user.html", user=row)


# ============================================================
# POLICY PAGES
# ============================================================

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


# ============================================================
# RUN APP
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
