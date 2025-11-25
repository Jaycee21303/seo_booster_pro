from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import os
import psycopg2
import psycopg2.extras
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# ------------------------------
# FLASK APP
# ------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")


# ------------------------------
# DATABASE CONNECTION
# ------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")


def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# ------------------------------
# SAFE DB INIT (NO DATA LOSS)
# ------------------------------
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            is_pro BOOLEAN DEFAULT FALSE,
            scans_used INTEGER DEFAULT 0,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            subscription_status TEXT,
            current_period_end TIMESTAMP
        );
    """)

    # Ensure admin user exists (ID = 1)
    cur.execute("""
        INSERT INTO users (id, email, password, is_admin, is_pro)
        VALUES (1, 'admin@admin.com', %s, TRUE, TRUE)
        ON CONFLICT (id) DO UPDATE SET
            email = EXCLUDED.email,
            password = EXCLUDED.password,
            is_admin = TRUE,
            is_pro = TRUE;
    """, (generate_password_hash("M4ry321!"),))

    conn.commit()
    cur.close()
    conn.close()


init_db()


# ------------------------------
# LOGIN REQUIRED DECORATOR
# ------------------------------
def require_login(f):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


def require_admin(f):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        if not session.get("is_admin"):
            return "Access denied"
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


# ------------------------------
# ROUTES
# ------------------------------

@app.route("/")
def index():
    return render_template("landing.html")


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        conn.close()

        if not user:
            return render_template("login.html", error="Invalid login")

        if not check_password_hash(user["password"], password):
            return render_template("login.html", error="Invalid login")

        session["user_id"] = user["id"]
        session["email"] = user["email"]
        session["is_admin"] = user["is_admin"]

        return redirect("/dashboard")

    return render_template("login.html")


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# DASHBOARD (USER)
@app.route("/dashboard")
@require_login
def dashboard():
    return render_template("dashboard.html")


# SETTINGS
@app.route("/settings")
@require_login
def settings():
    return render_template("settings.html")


# ------------------------------
# ADMIN PANEL — OPTION A FEATURES
# ------------------------------

@app.route("/admin/users")
@require_admin
def admin_users():
    search = request.args.get("search", "")
    sort = request.args.get("sort", "id_desc")

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    base_query = "SELECT * FROM users WHERE email ILIKE %s"
    search_like = f"%{search}%"

    # Sorting
    if sort == "id_asc":
        order = " ORDER BY id ASC"
    elif sort == "email":
        order = " ORDER BY email ASC"
    else:
        order = " ORDER BY id DESC"

    cur.execute(base_query + order, (search_like,))
    users = cur.fetchall()

    conn.close()

    return render_template(
        "admin_users.html",
        users=users,
        search=search,
        sort=sort
    )


# DELETE USER
@app.route("/admin/delete/<int:user_id>", methods=["POST"])
@require_admin
def admin_delete_user(user_id):
    if user_id == 1:
        return "Cannot delete admin."

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    conn.commit()
    conn.close()

    return redirect("/admin/users")


# RESET SCANS
@app.route("/admin/reset-scans/<int:user_id>", methods=["POST"])
@require_admin
def admin_reset_scans(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET scans_used=0 WHERE id=%s", (user_id,))
    conn.commit()
    conn.close()

    return redirect("/admin/users")


# TOGGLE PRO STATUS
@app.route("/admin/toggle-pro/<int:user_id>", methods=["POST"])
@require_admin
def admin_toggle_pro(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET is_pro = NOT is_pro
        WHERE id=%s
    """, (user_id,))
    conn.commit()
    conn.close()

    return redirect("/admin/users")


# 404 FIX
@app.errorhandler(404)
def page_not_found(e):
    return render_template("landing.html"), 404


# ------------------------------
# RUN
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
