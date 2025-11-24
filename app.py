from flask import Flask, render_template, request, redirect, session, send_file
from utils.db import init_db, fetch_one, fetch_all, execute
from utils.analyzer import run_local_seo_analysis
from utils.pdf_builder import generate_pdf_report
import os
import tempfile


# -------------------------------------------------
# FLASK APP SETUP
# -------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "devsecret123")


# -------------------------------------------------
# DB INIT
# -------------------------------------------------
init_db()


# -------------------------------------------------
# HELPERS
# -------------------------------------------------
def current_user():
    if "user_id" not in session:
        return None
    return fetch_one("SELECT * FROM users WHERE id=%s", (session["user_id"],))


def is_pro(user):
    return user.get("is_pro", False)


# -------------------------------------------------
# LANDING PAGE
# -------------------------------------------------
@app.route("/")
def landing():
    return render_template("landing.html")


# -------------------------------------------------
# LOGIN
# -------------------------------------------------
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


# -------------------------------------------------
# SIGNUP
# -------------------------------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        existing = fetch_one("SELECT * FROM users WHERE email=%s", (email,))
        if existing:
            return render_template("signup.html", error="Email already registered")

        execute(
            "INSERT INTO users (email, password, scans_used, is_pro) VALUES (%s, %s, 0, FALSE)",
            (email, password)
        )

        return redirect("/login")

    return render_template("signup.html")


# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    user = current_user()
    if not user:
        return redirect("/login")

    user["is_pro"] = is_pro(user)

    keyword_score = None
    site_audit = None
    optimization_tips = None

    # Subscores
    content_score = None
    technical_score_value = None
    keyword_score_value = None
    onpage_score = None
    link_score = None

    competitor_data = None

    if request.method == "POST":
        url = request.form.get("website_url")
        keyword = request.form.get("keyword")
        competitor_url = request.form.get("competitor_url")

        # FREE LIMIT CHECK
        if not user["is_pro"] and user["scans_used"] >= 3:
            return render_template("dashboard.html", limit_reached=True)

        # RUN MAIN ANALYZER
        (
            keyword_score,
            site_audit,
            optimization_tips,
            content_score,
            technical_score_value,
            keyword_score_value,
            onpage_score,
            link_score
        ) = run_local_seo_analysis(url, keyword)

        # increment free-tier usage
        if not user["is_pro"]:
            execute("UPDATE users SET scans_used=scans_used+1 WHERE id=%s", (user["id"],))

        # OPTIONAL COMPETITOR SCAN
        if competitor_url and competitor_url.strip() != "":
            (
                comp_main_score,
                comp_audit,
                comp_tips,
                comp_content_score,
                comp_technical,
                comp_keyword,
                comp_onpage,
                comp_link
            ) = run_local_seo_analysis(competitor_url, keyword)

            competitor_data = {
                "score": comp_main_score,
                "audit": comp_audit,
                "tips": comp_tips,
                "content_score": comp_content_score,
                "technical_score": comp_technical,
                "keyword_score": comp_keyword,
                "onpage_score": comp_onpage,
                "link_score": comp_link
            }

        # SAVE SCAN FOR PDF EXPORT
        session["last_scan"] = {
            "url": url,
            "main_score": keyword_score,
            "content_score": content_score,
            "technical_score": technical_score_value,
            "keyword_score": keyword_score_value,
            "onpage_score": onpage_score,
            "link_score": link_score,
            "audit": site_audit,
            "tips": optimization_tips,
            "competitor_data": competitor_data
        }

    return render_template(
        "dashboard.html",
        user=user,
        limit_reached=False,
        keyword_score=keyword_score,
        site_audit=site_audit,
        optimization_tips=optimization_tips,
        content_score=content_score,
        technical_score=technical_score_value,
        keywordcore=keyword_score_value,
        onpage_score=onpage_score,
        link_score=link_score,
        competitor_data=competitor_data
    )


# -------------------------------------------------
# EXPORT PDF
# -------------------------------------------------
@app.route("/export-pdf")
def export_pdf():
    user = current_user()
    if not user:
        return redirect("/login")

    if "last_scan" not in session:
        return "No scan available to export."

    scan = session["last_scan"]

    temp_path = tempfile.mktemp(suffix=".pdf")

    generate_pdf_report(
        temp_path,
        scan["url"],
        scan["main_score"],
        scan["content_score"],
        scan["technical_score"],
        scan["keyword_score"],
        scan["onpage_score"],
        scan["link_score"],
        scan["audit"],
        scan["tips"],
        scan.get("competitor_data")
    )

    return send_file(
        temp_path,
        as_attachment=True,
        download_name="seo_report.pdf",
        mimetype="application/pdf"
    )


# -------------------------------------------------
# SETTINGS PAGE
# -------------------------------------------------
@app.route("/settings", methods=["GET", "POST"])
def settings():
    user = current_user()
    if not user:
        return redirect("/login")

    if request.method == "POST":
        api_key = request.form.get("api_key")
        execute("UPDATE users SET api_key=%s WHERE id=%s", (api_key, user["id"]))
        return redirect("/settings")

    user = current_user()
    return render_template("settings.html", user=user)


# -------------------------------------------------
# LOGOUT
# -------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -------------------------------------------------
# RUN APP
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
