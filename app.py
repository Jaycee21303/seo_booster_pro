import os
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db import fetch_one, fetch_all, execute

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecret")


# ============================================================
# AUTO-CREATE ADMIN (ID = 1)
# ============================================================

def ensure_admin_exists():
    """Creates or updates the built-in admin user (ID=1)."""
    execute("""
        INSERT INTO users (id, email, password, is_pro, is_admin, scans_used)
        VALUES (1, 'admin@admin.com', %s, TRUE, TRUE, 0)
        ON CONFLICT (id)
        DO UPDATE SET
            email = EXCLUDED.email,
            password = EXCLUDED.password,
            is_admin = TRUE;
    """, (generate_password_hash("M4ry321!"),))
    print("✓ Admin ensured: admin@admin.com / M4ry321!")


ensure_admin_exists()


# ============================================================
# SESSION HELPERS
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
            INSERT INTO users (email, password)
            VALUES (%s, %s)
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
# USER DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect("/login")
    return render_template("dashboard.html", user=user)


@app.route("/settings")
def settings():
    user = current_user()
    if not user:
        return redirect("/login")
    return render_template("settings.html", user=user)


# ============================================================
# ADMIN — USERS LIST
# ============================================================

@app.route("/admin/users")
def admin_users():
    if not admin_required():
        return "Access Denied"

    # Search
    q = request.args.get("q", "").strip().lower()

    # Sorting
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

    # Query
    if q:
        users = fetch_all(f"""
            SELECT * FROM users
            WHERE LOWER(email) LIKE %s
            ORDER BY {order_sql}
        """, (f"%{q}%",))
    else:
        users = fetch_all(f"SELECT * FROM users ORDER BY {order_sql}")

    return render_template("admin_users.html",
                           users=users,
                           q=q,
                           sort=sort)


# ============================================================
# ADMIN — EDIT USER
# ============================================================

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


# ============================================================
# ADMIN — DELETE USER
# ============================================================

@app.route("/admin/delete/<int:user_id>")
def admin_delete_user(user_id):
    if not admin_required():
        return "Access Denied"

    execute("DELETE FROM users WHERE id=%s", (user_id,))
    return redirect("/admin/users")


# ============================================================
# ADMIN — RESET USER SCAN COUNT
# ============================================================

@app.route("/admin/reset_scans/<int:user_id>")
def admin_reset_scans(user_id):
    if not admin_required():
        return "Access Denied"

    execute("UPDATE users SET scans_used=0 WHERE id=%s", (user_id,))
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
# RUN APP
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
