from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
import stripe, requests, re, os
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# DB layer
from utils.db import fetch_one, fetch_all, execute

# PDF generator
from utils.pdf_builder import generate_pdf_report

# Stripe keys
from config import (
    STRIPE_PUBLIC_KEY,
    STRIPE_SECRET_KEY,
    STRIPE_PRICE_ID,
    WEBHOOK_SECRET
)

app = Flask(__name__)
app.secret_key = "super-secret-key"
stripe.api_key = STRIPE_SECRET_KEY


# ===================================================================
# AUTO-CREATE ADMIN USER (ID = 1)
# ===================================================================

def ensure_admin_exists():
    """
    Ensures admin always exists with ID=1.
    Updates password/is_pro/is_admin if row already exists.
    """
    execute("""
        INSERT INTO users (id, email, password, is_pro, is_admin, scans_used)
        VALUES (1, 'admin@admin.com', 'M4ry321!', TRUE, TRUE, 0)
        ON CONFLICT (id)
        DO UPDATE SET 
            email=EXCLUDED.email,
            password=EXCLUDED.password,
            is_pro=TRUE,
            is_admin=TRUE;
    """)
    print("✔ Admin user ensured: admin@admin.com / M4ry321!")


# ===================================================================
# SEO ENGINE
# ===================================================================

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


# -------- Full Analyzer --------

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


# ===================================================================
# AI TEXT OUTPUTS
# ===================================================================

def ai_summary(data):
    return f"Your site scored {data['score']}. Solid foundation — small updates to structure, keyword usage, and technical signals can boost rankings fast."

def ai_action_plan(data):
    return "Improve headings, expand keyword usage, fix missing alt tags, and check technical signals for a strong SEO boost."

def ai_google_thinks(data):
    return "Google sees helpful content but under-optimized structure. Improve clarity, metadata, and technical reliability."

def ai_competitor_summary(main, comp):
    return f"Your site scored {main['score']} vs competitor {comp['score']}. They lead in content depth; you lead in technical structure."

def ai_competitor_advantages(main, comp):
    return "Competitor has deeper content structure and stronger keyword embedding."

def ai_competitor_disadvantages(main, comp):
    return "Competitor struggles with weak internal links and missing alt tags — your advantage."


# ===================================================================
# FULL SCAN ENGINE
# ===================================================================

def run_full_scan(url, keyword=None, competitor_url=None):
    html = fetch_html(url)
    if not html:
        return {"error": "unreachable"}

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
            response["competitor_data"] = comp
            response["competitor_summary"] = ai_competitor_summary(main, comp)
            response["competitor_advantages"] = ai_competitor_advantages(main, comp)
            response["competitor_disadvantages"] = ai_competitor_disadvantages(main, comp)
        else:
            response["competitor_data"] = None

    return response


# ===================================================================
# AUTH ROUTES
# ===================================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        execute("""
            INSERT INTO users (email, password, is_pro, is_admin)
            VALUES (%s, %s, FALSE, FALSE)
        """, (email, password))

        user = fetch_one("SELECT id FROM users WHERE email=%s", (email,))
        session["user_id"] = user["id"]
        session["is_pro"] = False
        session["is_admin"] = False

        return redirect("/dashboard")

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = fetch_one("SELECT * FROM users WHERE email=%s", (email,))
        if not user or user["password"] != password:
            return render_template("login.html", error="Invalid email or password.")

        session["user_id"] = user["id"]
        session["is_pro"] = user["is_pro"]

        session["is_admin"] = (user["id"] == 1)

        return redirect("/dashboard")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ===================================================================
# DASHBOARD
# ===================================================================

@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect("/login")

    user = fetch_one("SELECT is_pro, scans_used FROM users WHERE id=%s", (session["user_id"],))

    scans_left = None if user["is_pro"] else max(0, 3 - user["scans_used"])

    return render_template(
        "dashboard.html",
        subscribed=user["is_pro"],
        scans_left=scans_left
    )


# ===================================================================
# SCAN ROUTE
# ===================================================================

@app.route("/scan", methods=["POST"])
def scan():
    if not session.get("user_id"):
        return jsonify({"error": "auth"}), 403

    user = fetch_one("SELECT is_pro, scans_used FROM users WHERE id=%s", (session["user_id"],))

    if not user["is_pro"] and user["scans_used"] >= 3:
        return jsonify({"error": "limit"}), 403

    if not user["is_pro"]:
        execute("UPDATE users SET scans_used=scans_used+1 WHERE id=%s", (session["user_id"],))

    data = request.get_json()
    result = run_full_scan(data.get("url"), data.get("keyword"), data.get("competitor"))

    session["latest_scan"] = result
    return jsonify(result)


# ===================================================================
# PDF EXPORT
# ===================================================================

@app.route("/export-pdf")
def export_pdf():
    data = session.get("latest_scan")
    if not data:
        return "No scan available.", 400

    filepath = "/tmp/seo_report.pdf"

    generate_pdf_report(
        filepath=filepath,
        url=data["url"],
        main_score=data["score"],
        content_score=data["content"],
        technical_score=data["technical"],
        keyword_score=data["keyword"],
        onpage_score=data["onpage"],
        link_score=data["links"],
        audit_text=data["audit"],
        tips_text=data["tips"],
        competitor_data=data.get("competitor_data")
    )

    return send_file(filepath, as_attachment=True, download_name="SEO_Report.pdf")


# ===================================================================
# STRIPE
# ===================================================================

@app.route("/pricing")
def pricing():
    return render_template("pricing.html", stripe_public_key=STRIPE_PUBLIC_KEY)


@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            allow_promotion_codes=True,
            success_url=url_for("success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("cancel", _external=True),
        )
        return jsonify({"url": checkout_session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/success")
def success():
    if session.get("user_id"):
        execute("UPDATE users SET is_pro=TRUE WHERE id=%s", (session["user_id"],))
        session["is_pro"] = True
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
    except:
        return "Webhook Error", 400

    if event["type"] == "customer.subscription.deleted":
        if session.get("user_id"):
            execute("UPDATE users SET is_pro=FALSE WHERE id=%s", (session["user_id"],))
            session["is_pro"] = False

    return "", 200


# ===================================================================
# ADMIN ROUTES
# ===================================================================

@app.route("/admin/users")
def admin_users():
    if session.get("user_id") != 1:
        return "Access denied", 403

    users = fetch_all(
        "SELECT id, email, is_pro, scans_used FROM users ORDER BY id DESC"
    )

    return render_template("admin_users.html", users=users)


@app.route("/admin/set_pro/<int:user_id>/<int:status>")
def admin_set_pro(user_id, status):
    if session.get("user_id") != 1:
        return "Access denied", 403

    execute("UPDATE users SET is_pro=%s WHERE id=%s", (bool(status), user_id))
    return redirect("/admin/users")


# ============================================
# TEMP FIX: Add is_admin column if missing
# ============================================
@app.route("/fixdb")
def fixdb():
    try:
        execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;
        """)
        return "DB FIXED: is_admin column ensured.", 200
    except Exception as e:
        return f"ERROR: {str(e)}", 500


# ===================================================================
# RUN + AUTO-ADMIN
# ===================================================================

ensure_admin_exists()

if __name__ == "__main__":
    app.run(debug=True)
