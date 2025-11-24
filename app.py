from flask import Flask, render_template, request, redirect, session
from utils.db import init_db, fetch_one, fetch_all, execute
from utils.analyzer import run_seo_analysis
import os

app = Flask(__name__)

# -----------------------------
# SECRET KEY (for sessions)
# -----------------------------
app.secret_key = os.environ.get("SECRET_KEY", "devsecret123")

# -----------------------------
# INIT DATABASE
# -----------------------------
init_db()


# -----------------------------
# LANDING PAGE
# -----------------------------
@app.route("/")
def landing():
    return render_template("landing.html")


# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = fetch_one(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )

        if user:
            session["user_id"] = user["id"]
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")


# -----------------------------
# SIGNUP
# -----------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        existing = fetch_one("SELECT * FROM users WHERE email=%s", (email,))
        if existing:
            return render_template("signup.html", error="Email already registered")

        execute(
            "INSERT INTO users (email, password) VALUES (%s, %s)",
            (email, password)
        )
        return redirect("/login")

    return render_template("signup.html")


# -----------------------------
# DASHBOARD (NOW 100% LOCAL ENGINE)
# -----------------------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    keyword_score = None
    site_audit = None
    optimization_tips = None
    suggested_keywords = None
    json_data = None

    if request.method == "POST":
        url = request.form.get("website_url")
        manual_keyword = request.form.get("keyword", "").strip()

        try:
            # Run full local SEO engine
            score, audit_text, tips_text, suggestions, json_output = run_seo_analysis(
                url, manual_keyword
            )

            keyword_score = score
            site_audit = audit_text
            optimization_tips = tips_text
            suggested_keywords = suggestions
            json_data = json_output

        except Exception as e:
            site_audit = f"An error occurred during analysis: {str(e)}"
            optimization_tips = ""
            suggested_keywords = []
            json_data = {}

    return render_template(
        "dashboard.html",
        keyword_score=keyword_score,
        site_audit=site_audit,
        optimization_tips=optimization_tips,
        suggested_keywords=suggested_keywords,
        json_data=json_data
    )


# -----------------------------
# SETTINGS (No API Keys Needed)
# -----------------------------
@app.route("/settings")
def settings():
    return render_template("settings.html")


# -----------------------------
# LOGOUT
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -----------------------------
# RUN (local dev only)
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
