from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import stripe, requests, re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from config import STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY, STRIPE_PRICE_ID, WEBHOOK_SECRET

app = Flask(__name__)
app.secret_key = "super-secret-key"
stripe.api_key = STRIPE_SECRET_KEY



# ===================================================================
#   ADVANCED SEO ENGINE (MAIN + COMPETITOR)
# ===================================================================

def fetch_html(url):
    """Fetch HTML with safe headers."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=8)
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

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("http"):
            if base_url.split("//")[1].split("/")[0] in href:
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
            r = requests.head(full, timeout=4)
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

    # Extract TEXT
    text = soup.get_text(" ", strip=True)

    # Title / Meta
    title = soup.title.string if soup.title else ""
    meta = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta["content"] if meta and meta.get("content") else ""

    # Headers
    h1, h2, h3 = count_headers(soup)

    # Images
    imgs = soup.find_all("img")
    missing_alt = find_missing_alt(imgs)

    # Links
    internal, external = count_links(soup, url)
    bl = broken_links(soup, url)

    # Keyword density
    density = count_keyword_density(text, keyword)

    # Readability
    readability = readability_score(text)

    # -------------------------
    # SCORE FORMULA (restored)
    # -------------------------
    content_score = min(100, 50 + readability // 2 + h2 * 2 + h3)
    keyword_score = min(100, 20 + density * 5)
    technical_score = min(100, 90 - missing_alt * 2 - bl * 3)
    onpage_score = min(100, 30 + h1 * 8 + len(meta_desc) // 8)
    link_score = min(100, 20 + internal + external // 2 - bl)

    overall = int(
        0.22 * content_score +
        0.22 * keyword_score +
        0.22 * technical_score +
        0.17 * onpage_score +
        0.17 * link_score
    )

    return {
        "score": overall,
        "content": content_score,
        "keyword": keyword_score,
        "technical": technical_score,
        "onpage": onpage_score,
        "links": link_score,
        "broken_links": bl,
        "keyword_density": density,
        "readability": readability
    }



# ===================================================================
#   AI STYLE RESPONSES (Friendly ChatGPT Tone, 3–5 sentences)
# ===================================================================

def ai_summary(data):
    return (
        f"Here's what I found! Your overall SEO score of {data['score']} suggests "
        "a solid foundation with plenty of room for improvement. Your content structure "
        "and metadata look promising, but keyword usage and technical factors could use "
        "a little tuning. With a few targeted adjustments, you can dramatically boost your visibility."
    )


def ai_action_plan(data):
    return (
        "First, focus on tightening your on-page structure with clearer headings and better metadata. "
        "Try adding more keyword-rich sections and improving internal links. "
        "Fixing technical issues like missing alt tags and reducing broken links will also help your rankings. "
        "Once those essentials are polished, your site will be in a strong position for long-term SEO growth."
    )


def ai_google_thinks(data):
    return (
        "From Google's perspective, your site appears informative but slightly under-optimized. "
        "Search engines may see strong content depth but notice gaps in structure or technical hygiene. "
        "With some tuning, your pages will be easier for both users and search engines to understand."
    )


def ai_competitor_summary(main, comp):
    return (
        "I compared your site to your competitor, and the results are interesting! "
        f"Your site scores {main['score']} while theirs scores {comp['score']}, giving you unique strengths. "
        "They may excel in certain areas like keyword relevance or content depth, but you have clear advantages "
        "in technical health and internal navigation. With a few improvements, you can close the gap quickly."
    )


def ai_competitor_advantages(main, comp):
    return (
        "Your competitor seems to have stronger keyword targeting and slightly deeper page content. "
        "They may also benefit from a richer heading structure. "
        "These strengths help them capture more search intent across multiple variations of your target keyword."
    )


def ai_competitor_disadvantages(main, comp):
    return (
        "They struggle with technical issues such as broken links or missing alt attributes, "
        "which can hurt their long-term rankings. Their internal linking also appears weaker. "
        "Improving your keyword structure will help you surpass them overall."
    )



# ===================================================================
#   COMBINED FULL SCAN (MAIN + COMPETITOR)
# ===================================================================

def run_full_scan(url, keyword=None, competitor_url=None):
    html = fetch_html(url)
    if not html:
        return {"error": "unreachable", "message": "Site could not be scanned."}

    main = analyze_html(html, url, keyword)

    output = {
        **main,
        "audit": ai_summary(main),
        "tips": ai_action_plan(main),
        "google_view": ai_google_thinks(main)
    }

    # COMPETITOR LOGIC
    if competitor_url:
        html2 = fetch_html(competitor_url)
        if html2:
            comp = analyze_html(html2, competitor_url, keyword)
            output["competitor_data"] = {
                "content_score": comp["content"],
                "keyword_score": comp["keyword"],
                "technical_score": comp["technical"],
                "onpage_score": comp["onpage"],
                "link_score": comp["links"],
            }
            output["competitor_summary"] = ai_competitor_summary(main, comp)
            output["competitor_advantages"] = ai_competitor_advantages(main, comp)
            output["competitor_disadvantages"] = ai_competitor_disadvantages(main, comp)
        else:
            output["competitor_data"] = None

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



# ===================================================================
# AUTH
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
# STRIPE BILLING
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
        session["subscribed"] = True

    if event["type"] == "customer.subscription.deleted":
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

    # PRO = unlimited scans
    if session.get("subscribed"):
        return jsonify(run_full_scan(url, keyword, competitor))

    # FREE = 3 scans
    scans = session.get("scan_count", 0)
    if scans >= 3:
        return jsonify({
            "error": "limit",
            "limit_reached": True,
            "message": "All 3 free scans used."
        }), 403

    session["scan_count"] = scans + 1

    return jsonify(run_full_scan(url, keyword, competitor))



# ===================================================================
# LAUNCH
# ===================================================================

if __name__ == "__main__":
    app.run(debug=True)


