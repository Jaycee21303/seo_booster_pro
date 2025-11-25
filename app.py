from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import stripe, requests, re, os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from utils.pdf_builder import generate_pdf_report
from db import fetch_one, fetch_all, execute   # <= YOUR DATABASE SYSTEM

# --------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------
from config import (
    STRIPE_PUBLIC_KEY,
    STRIPE_SECRET_KEY,
    STRIPE_PRICE_ID,
    WEBHOOK_SECRET,
)

app = Flask(__name__)
app.secret_key = "super-secret-key"
stripe.api_key = STRIPE_SECRET_KEY


# ==============================================================
# SEO ENGINE (unchanged — exact same logic you had)
# ==============================================================

def fetch_html(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        return r.text
    except:
        return None

def count_headers(soup):
    return (
        len(soup.find_all("h1")),
        len(soup.find_all("h2")),
        len(soup.find_all("h3")),
    )

def count_keyword_density(text, keyword):
    if not keyword:
        return 0
    return text.lower().count(keyword.lower())

def find_missing_alt(imgs):
    return sum(1 for img in imgs if not img.get("alt"))

def count_links(soup, base_url):
    internal = 0
    external = 0
    base_domain = base_url.split("//")[1].split("/")[0]

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("http"):
            if base_domain in href:
                internal += 1
            else:
                external += 1
        else:
            internal += 1

    return internal, external

def broken_links(soup, base_url):
    broken = 0
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(base_url, href)
        try:
            r = requests.head(full, timeout=5)
            if r.status_code >= 400:
                broken += 1
        except:
            broken += 1
    return broken

def readability_score(text):
    length = len(text.split())
    if length < 300:
        return 40
    elif length < 800:
        return 70
    else:
        return 90

def analyze_html(html, url, keyword=None):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    title = soup.title.string if soup.title else ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta_tag["content"] if meta_tag and meta_tag.get("content") else ""

    h1, h2, h3 = count_headers(soup)
    imgs = soup.find_all("img")
    missing_alt = find_missing_alt(imgs)

    internal, external = count_links(soup, url)
    bl = broken_links(soup, url)
    density = count_keyword_density(text, keyword)
    readability = readability_score(text)

    content_score = min(100, 50 + readability // 2 + h2 * 2 + h3)
    keyword_score = min(100, 20 + density * 5)
    technical_score = min(100, 90 - missing_alt * 2 - bl * 3)
    onpage_score = min(100, 30 + h1 * 8 + len(meta_desc) // 8)
    link_score = min(100, 20 + internal + external // 2 - bl)

    final_score = int(
        0.22 * content_score +
        0.22 * keyword_score +
        0.22 * technical_score +
        0.17 * onpage_score +
        0.17 * link_score
    )

    return {
        "score": final_score,
        "content": content_score,
        "keyword": keyword_score,
        "technical": technical_score,
        "onpage": onpage_score,
        "links": link_score,
        "broken_links": bl,
        "keyword_density": density,
        "readability": readability,
    }


# --------------------------------------------------------------
# AI TEXT (unchanged)
# --------------------------------------------------------------

def ai_summary(data):
    return (
        f"Great job running your scan! Your site scored {data['score']}. "
        "This shows you already have a solid base. With a few technical tune-ups and stronger keyword use, "
        "you can see easy wins."
    )

def ai_action_plan(data):
    return (
        "Improve your heading structure, meta descriptions, and internal linking. "
        "Fix missing alt tags and consider enriching content with additional keyword variations."
    )

def ai_google_thinks(data):
    return (
        "Google sees your site as useful but slightly under-optimized. "
        "More clarity in structure and technical polish can help rankings climb."
    )

def ai_competitor_summary(main, comp):
    return (
        f"Your score: {main['score']} vs competitor: {comp['score']}. "
        "They are strong in content depth, but you have an advantage in technical hygiene."
    )

def ai_competitor_advantages(main, comp):
    return (
        "Competitor has deeper keyword integration and more layered content organization."
    )

def ai_competitor_disadvantages(main, comp):
    return (
        "Competitor struggles with broken links, missing alt tags, and technical structure."
    )


# --------------------------------------------------------------
# FULL SCAN
# --------------------------------------------------------------

def run_full_scan(url, keyword=None, competitor_url=None):
    html = fetch_html(url)
    if not html:
        return {"error": "unreachable", "message": "Site could not be scanned."}

    main = analyze_html(html, url, keyword)

    response = {
        **main,
        "url": url,
        "audit": ai_summary(main),
        "tips": ai_action_plan(main),
        "google_view": ai_google_thinks(main),
    }

    if competitor_url:
        html2 = fetch_html(competitor_url)
        if html2:
            comp = analyze_html(html2, competitor_url, keyword)
            response["competitor_data"] = {
                "content_score": comp["content"],
                "keyword_score": comp["keyword"],
                "technical_score": comp["technical"],
                "onpage_score": comp["onpage"],
                "link_score": comp["links"]
            }
            response["competitor_summary"] = ai_competitor_summary(main, comp)
            response["competitor_advantages"] = ai_competitor_advantages(main, comp)
            response["competitor_disadvantages"] = ai_competitor_disadvantages(main, comp)
        else:
            response["competitor_data"] = None

    return response


# ==============================================================
# AUTH HELPERS
# ==============================================================

def current_user():
    if "user_id" not in session:
        return None
    return fetch_one("SELECT * FROM users WHERE id=%s", (session["user_id"],))

def login_required(func):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


# ==============================================================
# ROUTES
# ==============================================================

@app.route("/")
def index():
    return render_template("landing.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")

        exists = fetch_one("SELECT id FROM users WHERE email=%s", (email,))
        if exists:
            return render_template("signup.html", error="Email already registered.")

        hashed_pw = generate_password_hash(password)

        execute("""
            INSERT INTO users (email, password, scans_used, is_pro)
            VALUES (%s, %s, 0, FALSE)
        """, (email, hashed_pw))

        user = fetch_one("SELECT * FROM users WHERE email=%s", (email,))
        session["user_id"] = user["id"]

        return redirect("/dashboard")

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")

        user = fetch_one("SELECT * FROM users WHERE email=%s", (email,))
        if not user:
            return render_template("login.html", error="Invalid email or password.")

        if not check_password_hash(user["password"], password):
            return render_template("login.html", error="Incorrect password.")

        session["user_id"] = user["id"]
        return redirect("/dashboard")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ==============================================================
# DASHBOARD
# ==============================================================

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    subscribed = user["is_pro"]
    scans_left = None if subscribed else max(0, 3 - user["scans_used"])

    return render_template("dashboard.html",
                           subscribed=subscribed,
                           scans_left=scans_left)


# ==============================================================
# SCAN AJAX
# ==============================================================

@app.route("/scan", methods=["POST"])
@login_required
def scan():
    user = current_user()

    data = request.get_json()
    url = data.get("url")
    keyword = data.get("keyword")
    competitor = data.get("competitor")

    if not user["is_pro"]:
        if user["scans_used"] >= 3:
            return jsonify({"error": "limit"}), 403

        execute("UPDATE users SET scans_used = scans_used + 1 WHERE id=%s", (user["id"],))

    result = run_full_scan(url, keyword, competitor)
    session["latest_scan"] = result

    return jsonify(result)


# ==============================================================
# STRIPE
# ==============================================================

@app.route("/pricing")
def pricing():
    return render_template("pricing.html", stripe_public_key=STRIPE_PUBLIC_KEY)


@app.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    user = current_user()

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        allow_promotion_codes=True,
        success_url=url_for("success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=url_for("cancel", _external=True),
    )

    return jsonify({"url": checkout_session.url})


@app.route("/success")
@login_required
def success():
    user = current_user()
    execute("UPDATE users SET is_pro = TRUE WHERE id=%s", (user["id"],))
    return render_template("success.html")


@app.route("/cancel")
def cancel():
    return render_template("cancel.html")


@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except Exception as e:
        return f"Webhook Error: {e}", 400

    if event["type"] == "checkout.session.completed":
        email = event["data"]["object"]["customer_details"]["email"]

        execute("UPDATE users SET is_pro = TRUE WHERE email=%s", (email,))

    return "", 200


# ==============================================================
# PDF EXPORT
# ==============================================================

@app.route("/export-pdf")
@login_required
def export_pdf():

    data = session.get("latest_scan")
    if not data:
        return "No scan available.", 400

    filepath = "/tmp/seo_report.pdf"

    generate_pdf_report(
        filepath=filepath,
        url=data.get("url"),
        main_score=data.get("score"),
        content_score=data.get("content"),
        technical_score=data.get("technical"),
        keyword_score=data.get("keyword"),
        onpage_score=data.get("onpage"),
        link_score=data.get("links"),
        audit_text=data.get("audit"),
        tips_text=data.get("tips"),
        competitor_data=data.get("competitor_data")
    )

    return send_file(filepath, as_attachment=True, download_name="SEO_Report.pdf")


# ==============================================================
# ADMIN (VIEW ALL USERS)
# ==============================================================

@app.route("/admin/users")
def admin_users():
    users = fetch_all("SELECT id, email, is_pro, scans_used FROM users ORDER BY id DESC")
    return render_template("admin_users.html", users=users)


# ==============================================================
# GOOGLE LOGIN (placeholder)
# ==============================================================

@app.route("/google-login")
def google_login():
    return "Google login coming soon!"

# ==============================================================
# ADMIN USERS PAGE
# ==============================================================

@app.route("/admin/users")
def admin_users():
    users = fetch_all("SELECT * FROM users ORDER BY id DESC")
    return render_template("admin_users.html", users=users)

# ==============================================================
# SETTINGS PAGE (Change Password)
# ==============================================================

from werkzeug.security import check_password_hash, generate_password_hash

@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html")


@app.route("/change-password", methods=["POST"])
@login_required
def change_password():
    user = current_user()

    current_pw = request.form.get("current_password")
    new_pw = request.form.get("new_password")
    confirm_pw = request.form.get("confirm_password")

    # 1. Confirm current password is correct
    if not check_password_hash(user["password"], current_pw):
        return render_template("settings.html", error="Current password is incorrect.")

    # 2. New passwords must match
    if new_pw != confirm_pw:
        return render_template("settings.html", error="New passwords do not match.")

    # 3. Update DB with new hashed password
    hashed_pw = generate_password_hash(new_pw)

    execute("UPDATE users SET password=%s WHERE id=%s", (hashed_pw, user["id"]))

    return render_template("settings.html", success="Password updated successfully!")

# ==============================================================
# RUN SERVER
# ==============================================================

if __name__ == "__main__":
    app.run(debug=True)
