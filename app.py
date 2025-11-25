from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import stripe, requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from config import STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY, STRIPE_PRICE_ID, WEBHOOK_SECRET

app = Flask(__name__)
app.secret_key = "super-secret-key"

stripe.api_key = STRIPE_SECRET_KEY



# ===================================================================
# ADVANCED REALISTIC SEO SCAN ENGINE (MAIN + COMPETITOR)
# ===================================================================
def fetch_html(url):
    """Safely fetch page HTML."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code != 200:
            return None
        return r.text
    except:
        return None


def analyze_html(html, keyword=None):
    """Analyze SEO factors and return category scores."""
    soup = BeautifulSoup(html, "html.parser")

    # Title & Meta
    title = soup.title.string if soup.title else ""
    meta_desc = ""
    md = soup.find("meta", attrs={"name": "description"})
    if md and md.get("content"):
        meta_desc = md["content"]

    # Headings
    h1 = len(soup.find_all("h1"))
    h2 = len(soup.find_all("h2"))
    h3 = len(soup.find_all("h3"))

    # Keyword density
    body_text = soup.get_text(" ", strip=True).lower()
    keyword_density = body_text.count(keyword.lower()) if keyword else 0

    # Images
    imgs = soup.find_all("img")
    missing_alt = sum(1 for i in imgs if not i.get("alt"))

    # Links
    a_tags = soup.find_all("a", href=True)
    internal_links = 0
    external_links = 0
    for a in a_tags:
        href = a["href"]
        if href.startswith("http"):
            external_links += 1
        else:
            internal_links += 1

    # ----- SCORE CALCULATION -----
    content_score = min(100, 40 + h2 * 3 + h3 * 2)
    keyword_score = min(100, 20 + (keyword_density * 5))
    technical_score = min(100, 80 - (missing_alt * 3))
    onpage_score = min(100, 40 + (h1 * 10) + (len(meta_desc) // 5))
    link_score = min(100, 20 + internal_links + (external_links // 2))

    overall = int(
        0.25 * content_score +
        0.25 * technical_score +
        0.25 * onpage_score +
        0.25 * link_score
    )

    return {
        "score": overall,
        "content": content_score,
        "keyword": keyword_score,
        "technical": technical_score,
        "onpage": onpage_score,
        "links": link_score,
    }


def run_full_scan(url, keyword=None, competitor_url=None):
    """Runs full scan + competitor scan if provided."""
    html = fetch_html(url)
    if not html:
        return {"error": "unreachable", "message": "Site could not be scanned."}

    main = analyze_html(html, keyword)

    # Base JSON structure
    output = {
        "score": main["score"],
        "content": main["content"],
        "keyword": main["keyword"],
        "technical": main["technical"],
        "onpage": main["onpage"],
        "links": main["links"],
        "audit": (
            "• Improve site load speed.\n"
            "• Add missing alt tags.\n"
            "• Add structured data.\n"
            "• Improve metadata quality."
        ),
        "tips": (
            "• Increase keyword density.\n"
            "• Add more H2/H3 headings.\n"
            "• Improve internal linking.\n"
            "• Add sitemap.xml."
        )
    }

    # COMPETITOR LOGIC
    if competitor_url:
        html2 = fetch_html(competitor_url)
        if html2:
            comp = analyze_html(html2, keyword)
            output["competitor_data"] = {
                "content_score": comp["content"],
                "keyword_score": comp["keyword"],
                "technical_score": comp["technical"],
                "onpage_score": comp["onpage"],
                "link_score": comp["links"]
            }

    return output



# ===================================================================
# STATIC ROUTES
# ===================================================================
@app.route("/")
def index():
    return render_template("landing.html")


@app.route("/dashboard")
def dashboard():
    if not session.get("user"):
        return redirect("/login")

    subscribed = session.get("subscribed", False)
    scans = session.get("scan_count", 0)
    scans_left = None if subscribed else max(0, 3 - scans)

    return render_template(
        "dashboard.html",
        subscribed=subscribed,
        scans_left=scans_left
    )


@app.route("/settings")
def settings():
    if not session.get("user"):
        return redirect("/login")
    return render_template("settings.html")



# ===================================================================
# AUTH ROUTES
# ===================================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email and password:
            session["user"] = email
            return redirect("/dashboard")

        return render_template("login.html", error="Invalid login")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email and password:
            session["user"] = email
            session["subscribed"] = False
            session["scan_count"] = 0
            return redirect("/dashboard")

        return render_template("signup.html", error="Signup failed")

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")



# ===================================================================
# STRIPE / BILLING
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
    session["subscribed"] = True
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
        print("🔥 Subscription started")
    if event["type"] == "invoice.payment_succeeded":
        print("💰 Subscription renewed")
    if event["type"] == "customer.subscription.deleted":
        print("❌ Subscription canceled")
        session["subscribed"] = False

    return "", 200



# ===================================================================
# AJAX SCAN ENDPOINT
# ===================================================================
@app.route("/scan", methods=["POST"])
def scan():
    if not session.get("user"):
        return jsonify({"error": "auth", "message": "Login required"}), 403

    data = request.get_json()
    url = data.get("url")
    keyword = data.get("keyword")
    competitor = data.get("competitor")

    if not url:
        return jsonify({"error": "invalid", "message": "URL required"}), 400

    # PRO = unlimited
    if session.get("subscribed"):
        return jsonify(run_full_scan(url, keyword, competitor))

    # FREE USERS = limit 3
    count = session.get("scan_count", 0)
    if count >= 3:
        return jsonify({
            "error": "limit",
            "message": "All 3 free scans have been used.",
            "limit_reached": True
        }), 403

    # run scan
    session["scan_count"] = count + 1
    return jsonify(run_full_scan(url, keyword, competitor))



# ===================================================================
# RUN SERVER
# ===================================================================
if __name__ == "__main__":
    app.run(debug=True)

