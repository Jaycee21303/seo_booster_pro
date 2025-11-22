from flask import Flask, render_template, request, redirect, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db import init_db, fetch_one, fetch_all, execute
from utils.ai_tools import generate_title, generate_meta, generate_keywords, rewrite_homepage
from utils.analyzer import analyze_url

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET_KEY"

# Initialize DB tables
init_db()


# -----------------------------
# LANDING PAGE
# -----------------------------
@app.route("/")
def landing():
    return render_template("landing.html")


# -----------------------------
# SIGNUP
# -----------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"].lower().strip()
        password = request.form["password"]
        confirm = request.form["confirm"]

        if password != confirm:
            return render_template("signup.html", error="Passwords do not match")

        # Check for existing user
        existing = fetch_one("SELECT * FROM users WHERE email=%s", (email,))
        if existing:
            return render_template("signup.html", error="Email already exists")

        hashed = generate_password_hash(password)

        # Create user
        execute(
            "INSERT INTO users (email, password) VALUES (%s, %s)",
            (email, hashed)
        )

        # Auto-login
        user = fetch_one("SELECT * FROM users WHERE email=%s", (email,))
        session["user_id"] = user["id"]
        session["email"] = user["email"]

        return redirect("/dashboard")

    return render_template("signup.html")


# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].lower().strip()
        password = request.form["password"]

        user = fetch_one("SELECT * FROM users WHERE email=%s", (email,))
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            return redirect("/dashboard")

        return render_template("login.html", error="Invalid email or password")

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
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user = fetch_one("SELECT * FROM users WHERE id=%s", (session["user_id"],))
    last_url = user["last_url"] if user and "last_url" in user else ""

    return render_template("dashboard.html", last_url=last_url)


# -----------------------------
# SAVE URL (users.last_url + logs table)
# -----------------------------
@app.route("/save_url", methods=["POST"])
def save_url():
    if "user_id" not in session:
        return jsonify({"success": False})

    url = request.form["url"]

    # Save to users table
    execute("UPDATE users SET last_url=%s WHERE id=%s", (url, session["user_id"]))

    # Insert into logs history
    execute(
        "INSERT INTO logs (user_id, url) VALUES (%s, %s)",
        (session["user_id"], url)
    )

    return jsonify({"success": True})


# -----------------------------
# ANALYZE URL (Title + Meta)
# -----------------------------
@app.route("/analyze_url", methods=["POST"])
def analyze():
    if "user_id" not in session:
        return jsonify({"error": "Login required"})

    url = request.form["url"]
    extracted = analyze_url(url)
    return jsonify(extracted)


# -----------------------------
# AI TOOL ENDPOINTS
# -----------------------------
@app.route("/ai/title", methods=["POST"])
def ai_title():
    url = request.form["url"]
    return jsonify({"result": generate_title(url, session["user_id"])})


@app.route("/ai/meta", methods=["POST"])
def ai_meta():
    url = request.form["url"]
    return jsonify({"result": generate_meta(url, session["user_id"])})


@app.route("/ai/keywords", methods=["POST"])
def ai_keywords():
    url = request.form["url"]
    return jsonify({"result": generate_keywords(url, session["user_id"])})


@app.route("/ai/rewrite", methods=["POST"])
def ai_rewrite():
    url = request.form["url"]
    return jsonify({"result": rewrite_homepage(url, session["user_id"])})


# ------------------------------------------------------
# RUN
# ------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)

