from flask import Flask, render_template, request, redirect, session, url_for, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, datetime

from utils.analyzer import analyze_website
from utils.ai_tools import generate_title, generate_meta, rewrite_homepage, keyword_list
from utils.pdf_generator import create_pdf_report

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_TO_A_SECURE_RANDOM_KEY"


# -----------------------------
# DATABASE SETUP
# -----------------------------
def init_db():
    if not os.path.exists("database.db"):
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT,
            api_key TEXT,
            date_created TEXT
        )
        """)
        conn.commit()
        conn.close()

init_db()


def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# LOGIN REQUIRED DECORATOR
# -----------------------------
def login_required(route_function):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return route_function(*args, **kwargs)
    wrapper.__name__ = route_function.__name__
    return wrapper


# -----------------------------
# HOME ROUTE → REDIRECT TO LOGIN
# -----------------------------
@app.route("/")
def home():
    return redirect("/login")


# -----------------------------
# SIGNUP — NOW AUTO-LOGINS USER
# -----------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db()
        c = conn.cursor()

        try:
            hashed_pw = generate_password_hash(password)
            c.execute(
                "INSERT INTO users (email, password, date_created) VALUES (?, ?, ?)",
                (email, hashed_pw, str(datetime.datetime.now()))
            )
            conn.commit()

            # AUTO-LOGIN IMMEDIATELY
            c.execute("SELECT id FROM users WHERE email=?", (email,))
            new_user = c.fetchone()
            conn.close()

            session["user_id"] = new_user["id"]
            session["email"] = email

            return redirect("/dashboard")

        except Exception:
            conn.close()
            return render_template("signup.html", error="Email already exists.")

    return render_template("signup.html")


# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db()
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE email=?", (email,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            return redirect("/dashboard")

        return render_template("login.html", error="Invalid login credentials")

    return render_template("login.html")


# -----------------------------
# LOGOUT
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    results = None
    url = None

    if request.method == "POST":
        url = request.form["url"]
        results = analyze_website(url)

    return render_template("dashboard.html", results=results, url=url)


# -----------------------------
# SETTINGS — FIXED VERSION
# -----------------------------
@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        api_key = request.form["api_key"]
        c.execute("UPDATE users SET api_key=? WHERE id=?", (api_key, session["user_id"]))
        conn.commit()

    # SAFE ONE-TIME FETCH
    c.execute("SELECT api_key FROM users WHERE id=?", (session["user_id"],))
    row = c.fetchone()
    api_key = row["api_key"] if row else ""

    conn.close()

    return render_template("settings.html", api_key=api_key)


# -----------------------------
# AI TOOL ENDPOINTS
# -----------------------------
@app.route("/ai/title", methods=["POST"])
@login_required
def ai_title():
    return generate_title(request.form["analyze_url"], session["user_id"])


@app.route("/ai/meta", methods=["POST"])
@login_required
def ai_meta():
    return generate_meta(request.form["analyze_url"], session["user_id"])


@app.route("/ai/rewrite", methods=["POST"])
@login_required
def ai_rewrite():
    return rewrite_homepage(request.form["analyze_url"], session["user_id"])


@app.route("/ai/keywords", methods=["POST"])
@login_required
def ai_keywords():
    return keyword_list(request.form["analyze_url"], request.form["country"], session["user_id"])


# -----------------------------
# DOWNLOAD PDF REPORT
# -----------------------------
@app.route("/download_report", methods=["POST"])
@login_required
def download_report():
    data = request.form["report_data"]
    filename = create_pdf_report(data)
    return send_file(filename, as_attachment=True)


# -----------------------------
# RUN THE APP
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
