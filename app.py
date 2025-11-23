from flask import Flask, render_template, request, redirect, session
from utils.db import init_db, fetch_one, fetch_all, execute
import os

app = Flask(__name__)

# -----------------------------
# REQUIRED FIX – SECRET KEY
# -----------------------------
app.secret_key = os.environ.get("SECRET_KEY", "devsecret123")

# -----------------------------
#  INIT DATABASE
# -----------------------------
init_db()


# -----------------------------
#  LANDING PAGE
# -----------------------------
@app.route("/")
def landing():
    return render_template("landing.html")


# -----------------------------
#  LOGIN
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = fetch_one("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))

        if user:
            session["user_id"] = user["id"]
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")


# -----------------------------
#  SIGNUP
# -----------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        existing = fetch_one("SELECT * FROM users WHERE email=%s", (email,))
        if existing:
            return render_template("signup.html", error="Email already registered")

        execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, password))
        return redirect("/login")

    return render_template("signup.html")


# -----------------------------
#  DASHBOARD (requires login)
# -----------------------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    keyword_score = None
    site_audit = None
    optimization_tips = None
    suggested_keywords = None

    if request.method == "POST":
        url = request.form.get("website_url")
        manual_keyword = request.form.get("keyword", "").strip()

        # Auto-detect keyword if none provided
        if manual_keyword:
            keyword = manual_keyword
        else:
            keyword = detect_keywords_from_page(url)

        # Always generate suggestions
        suggested_keywords = generate_keyword_suggestions(url)

        # Run your main AI analysis here
        keyword_score, site_audit, optimization_tips = run_seo_analysis(url, keyword)

    return render_template(
        "dashboard.html",
        keyword_score=keyword_score,
        site_audit=site_audit,
        optimization_tips=optimization_tips,
        suggested_keywords=suggested_keywords
    )


# -----------------------------
#  SETTINGS PAGE
# -----------------------------
@app.route("/settings", methods=["GET", "POST"])
def settings():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        api_key = request.form.get("api_key")
        execute("UPDATE users SET api_key=%s WHERE id=%s", (api_key, session["user_id"]))
        return redirect("/settings")

    user = fetch_one("SELECT * FROM users WHERE id=%s", (session["user_id"],))
    return render_template("settings.html", user=user)


# -----------------------------
#  LOGOUT
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -----------------------------
#  RUN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
