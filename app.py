import os
from flask import Flask, render_template, request, redirect, session, jsonify, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from utils.db import fetch_one, fetch_all, execute

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecret")


# ============================================================
# AUTO-CREATE BUILT-IN ADMIN USER (ID = 1)
# ============================================================

def ensure_admin_exists():
    execute("""
        INSERT INTO users (id, email, password, is_pro, is_admin, scans_used, pdf_used)
        VALUES (1, 'admin@admin.com', %s, TRUE, TRUE, 0, 0)
        ON CONFLICT (id)
        DO UPDATE SET
            email = EXCLUDED.email,
            password = EXCLUDED.password,
            is_admin = TRUE;
    """, (generate_password_hash("M4ry321!"),))

    print("✓ Admin ensured: admin@admin.com / M4ry321!")


ensure_admin_exists()


# ============================================================
# HELPERS
# ============================================================

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return fetch_one("SELECT * FROM users WHERE id=%s", (uid,))


def admin_required():
    user = current_user()
    return user and user["is_admin"] is True


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
            INSERT INTO users (email, password, scans_used, pdf_used, is_pro, is_admin)
            VALUES (%s, %s, 0, 0, FALSE, FALSE)
        """, (email, hashed))

        row = fetch_one("SELECT id FROM users WHERE email=%s", (email,))
        session["user_id"] = row["id"]
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
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect("/login")

    # Free users get 2 scans per month
    scans_left = None if user["is_pro"] else max(0, 2 - user["scans_used"])

    return render_template("dashboard.html", user=user, scans_left=scans_left, subscribed=user["is_pro"])


@app.route("/settings")
def settings():
    if not current_user():
        return redirect("/login")
    return render_template("settings.html", user=current_user())


# ============================================================
# MAIN SCAN ROUTE
# ============================================================

@app.route("/scan", methods=["POST"])
def scan():
    user = current_user()
    if not user:
        return jsonify({"error": "auth"}), 401

    data = request.json
    url = data.get("url")
    keyword = data.get("keyword", "")
    competitor = data.get("competitor", "")

    # FREE USER LIMIT — 2 scans per month
    if not user["is_pro"]:
        if user["scans_used"] >= 2:
            return jsonify({"error": "limit"}), 403

        execute("UPDATE users SET scans_used = scans_used + 1 WHERE id=%s", (user["id"],))

    # Placeholder scan engine (replace with real later)
    score = 75
    content = 70
    keyword_score = 72
    technical = 69
    onpage = 80
    links = 64
    audit = "Site audit results..."
    tips = "SEO tips..."

    competitor_data = None
    competitor_summary = ""
    competitor_advantages = ""
    competitor_disadvantages = ""

    if competitor:
        competitor_data = {
            "content": 55,
            "keyword": 62,
            "technical": 58,
            "onpage": 63,
            "links": 52
        }
        competitor_summary = "Competitor summary..."
        competitor_advantages = "They have stronger content..."
        competitor_disadvantages = "Your site loads faster..."

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
# PDF EXPORT LIMITS
# ============================================================

@app.route("/export-pdf")
def export_pdf():
    user = current_user()
    if not user:
        return "Unauthorized", 401

    # Free users get *1 PDF per month*
    if not user["is_pro"]:
        if user["pdf_used"] >= 1:
            return "PDF limit reached. Upgrade to Pro.", 403

        execute("UPDATE users SET pdf_used = pdf_used + 1 WHERE id=%s", (user["id"],))

    # Placeholder file
    return "PDF GENERATED (placeholder)"


# ============================================================
# PRICING PAGE
# ============================================================

@app.route("/pricing")
def pricing():
    return render_template("pricing.html")


# ============================================================
# ADMIN PANEL
# ============================================================

@app.route("/admin/users")
def admin_users():
    if not admin_required():
        return "Access Denied"

    q = request.args.get("q", "").strip().lower()
    sort = request.args.get("sort", "id_desc")

    order_sql = {
        "id_asc": "id ASC",
        "id_desc": "id DESC",
        "email_asc": "LOWER(email) ASC",
        "email_desc": "LOWER(email) DESC",
        "pro_asc": "is_pro ASC",
        "pro_desc": "is_pro DESC",
        "scans_asc": "scans_used ASC",
        "scans_desc": "scans_used DESC",
    }.get(sort, "id DESC")

    if q:
        users = fetch_all(f"""
            SELECT * FROM users
            WHERE LOWER(email) LIKE %s
            ORDER BY {order_sql}
        """, (f"%{q}%",))
    else:
        users = fetch_all(f"SELECT * FROM users ORDER BY {order_sql}")

    return render_template("admin_users.html", users=users, q=q, sort=sort)


@app.route("/admin/edit/<int:user_id>", methods=["GET", "POST"])
def admin_edit_user(user_id):
    if not admin_required():
        return "Access Denied"

    user = fetch_one("SELECT * FROM users WHERE id=%s", (user_id,))
    if not user:
        return "User not found"

    if request.method == "POST":
        email = request.form["email"]
        is_pro = request.form.get("is_pro") == "on"
        is_admin = request.form.get("is_admin") == "on"

        execute("""
            UPDATE users
            SET email=%s, is_pro=%s, is_admin=%s
            WHERE id=%s
        """, (email, is_pro, is_admin, user_id))

        return redirect("/admin/users")

    return render_template("admin_edit_user.html", user=user)


@app.route("/admin/delete/<int:user_id>")
def admin_delete_user(user_id):
    if not admin_required():
        return "Access Denied"

    execute("DELETE FROM users WHERE id=%s", (user_id,))
    return redirect("/admin/users")


@app.route("/admin/reset_scans/<int:user_id>")
def admin_reset_scans(user_id):
    if not admin_required():
        return "Access Denied"

    execute("UPDATE users SET scans_used=0, pdf_used=0 WHERE id=%s", (user_id,))
    return redirect("/admin/users")


# ============================================================
# POLICY PAGES
# ============================================================

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/about")
def about():
    return render_template("about.html")


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
