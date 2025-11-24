import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import json

# ===============================
# CONFIG LIMITS FOR T1 (RENDER FREE)
# ===============================
MAX_HTML_CHARS = 3500
MAX_LINK_CHECKS = 25
MAX_IMAGES_CHECK = 40


# ===============================
# SIMPLE STOPWORDS LIST
# ===============================
STOPWORDS = set("""
the a an is are to of and in on for with by this that from at as be have has it its you your our their they we i 
""".split())


# ===============================
# FETCH PAGE
# ===============================
def fetch_page(url):
    try:
        response = requests.get(url, timeout=12, headers={
            "User-Agent": "Mozilla/5.0"
        })
        if response.status_code == 200:
            return response.text
        return None
    except:
        return None


# ===============================
# PARSE TEXT
# ===============================
def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ")
    return text[:MAX_HTML_CHARS]


# ===============================
# EXTRACT TITLE, META, HEADINGS
# ===============================
def parse_structure(html):
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.text.strip() if soup.title else ""
    meta_desc = ""
    tag = soup.find("meta", attrs={"name": "description"})
    if tag and tag.get("content"):
        meta_desc = tag["content"]

    h1s = [h.get_text(" ").strip() for h in soup.find_all("h1")]
    h2s = [h.get_text(" ").strip() for h in soup.find_all("h2")]
    h3s = [h.get_text(" ").strip() for h in soup.find_all("h3")]

    return title, meta_desc, h1s, h2s, h3s


# ===============================
# KEYWORD EXTRACTION
# ===============================
def extract_keywords(text, limit=10):
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    freq = {}

    for w in words:
        if w not in STOPWORDS:
            freq[w] = freq.get(w, 0) + 1

    # sort by frequency
    ranked = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, c in ranked[:limit]]


# ===============================
# KEYWORD SUGGESTIONS (LOCAL)
# ===============================
def generate_keyword_suggestions(text):
    kw = extract_keywords(text, limit=20)
    return kw[:5]


# ===============================
# KEYWORD DENSITY
# ===============================
def keyword_density(text, keyword):
    words = text.lower().split()
    if len(words) == 0:
        return 0
    count = words.count(keyword.lower())
    return round((count / len(words)) * 100, 2)


# ===============================
# IMAGE ALT CHECKING
# ===============================
def analyze_images(html):
    soup = BeautifulSoup(html, "html.parser")
    images = soup.find_all("img")

    results = {
        "total": len(images),
        "missing_alt": 0,
        "keyword_alt": 0,
        "bad_alt": 0
    }

    for i, img in enumerate(images):
        if i >= MAX_IMAGES_CHECK:
            break

        alt = img.get("alt", "").strip().lower()
        if not alt:
            results["missing_alt"] += 1
        elif len(alt) < 3:
            results["bad_alt"] += 1

    return results


# ===============================
# LINK ANALYSIS + BROKEN LINK CHECKING
# ===============================
def analyze_links(html, url):
    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.find_all("a")
    base = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(url))

    internal = 0
    external = 0
    broken = []

    checked = 0

    for a in anchors:
        if checked >= MAX_LINK_CHECKS:
            break

        href = a.get("href")
        if not href:
            continue

        full = urljoin(base, href)

        # count internal/external
        if urlparse(full).netloc == urlparse(url).netloc:
            internal += 1
        else:
            external += 1

        # broken link check
        try:
            r = requests.head(full, timeout=4)
            if r.status_code >= 400:
                broken.append(full)
        except:
            broken.append(full)

        checked += 1

    return internal, external, broken


# ===============================
# CANONICAL, ROBOTS, SITEMAP
# ===============================
def analyze_meta_files(html, url):
    soup = BeautifulSoup(html, "html.parser")
    canonical = None
    tag = soup.find("link", rel="canonical")
    if tag and tag.get("href"):
        canonical = tag["href"]

    # robots.txt
    base = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(url))
    robots_url = base + "/robots.txt"

    robots = None
    try:
        r = requests.get(robots_url, timeout=4)
        if r.status_code == 200:
            robots = r.text[:500]
    except:
        robots = None

    # sitemap
    sitemap_url = base + "/sitemap.xml"
    sitemap = None
    try:
        r = requests.get(sitemap_url, timeout=4)
        if r.status_code == 200:
            sitemap = True
    except:
        sitemap = False

    return canonical, robots, sitemap


# ===============================
# SCHEMA DETECTION
# ===============================
def detect_schema(html):
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", type="application/ld+json")
    schemas = []

    for s in scripts:
        try:
            data = json.loads(s.string)
            schemas.append(data.get("@type", "Unknown"))
        except:
            continue

    return schemas


# ===============================
# PAGE SPEED HEURISTICS
# ===============================
def analyze_speed(html):
    soup = BeautifulSoup(html, "html.parser")

    js = soup.find_all("script")
    css = soup.find_all("link", rel="stylesheet")
    imgs = soup.find_all("img")

    return {
        "js_files": len(js),
        "css_files": len(css),
        "image_count": len(imgs)
    }


# ===============================
# FINAL SEO SCORE CALCULATION
# ===============================
def compute_score(title, meta, h1s, text, density, images, linkdata, canonical, schemas):
    score = 0

    # Title
    if title:
        score += 10
        if len(title) > 20 and len(title) < 70:
            score += 5

    # Meta
    if meta:
        score += 10

    # H1
    if len(h1s) == 1:
        score += 10

    # Keyword density
    if density > 0.3:
        score += 10
    if density > 1:
        score += 5
    if density > 3:
        score -= 5  # too high

    # Word count
    wc = len(text.split())
    if wc > 300:
        score += 10
    if wc > 700:
        score += 5

    # Images w/ alt
    if images["missing_alt"] == 0:
        score += 10

    # Broken links
    broken = linkdata[2]
    if len(broken) == 0:
        score += 10
    else:
        score -= len(broken) * 2

    # Canonical
    if canonical:
        score += 5

    # Schema
    if schemas:
        score += 10

    return max(0, min(100, score))


# ===============================
# MAIN LOCAL SEO ENGINE
# ===============================
def run_seo_analysis(url, keyword):
    html = fetch_page(url)
    if not html:
        return {
            "score": 0,
            "audit_text": "Could not load page.",
            "tips_text": "",
            "json": {}
        }

    text = extract_text(html)
    title, meta, h1s, h2s, h3s = parse_structure(html)

    # keyword detection fallback
    if not keyword:
        kws = extract_keywords(text)
        keyword = kws[0] if kws else ""

    # density
    density = keyword_density(text, keyword)

    # image audit
    images = analyze_images(html)

    # link audit
    internal, external, broken = analyze_links(html, url)

    # meta files
    canonical, robots, sitemap = analyze_meta_files(html, url)

    # schema
    schemas = detect_schema(html)

    # speed
    speed = analyze_speed(html)

    # score
    score = compute_score(title, meta, h1s, text, density, images, (internal, external, broken), canonical, schemas)

    # keyword suggestions
    suggestions = generate_keyword_suggestions(text)

    # ===========================
    # BUILD JSON OUTPUT
    # ===========================
    json_output = {
        "title": title,
        "meta_description": meta,
        "h1": h1s,
        "keyword": keyword,
        "keyword_density": density,
        "word_count": len(text.split()),
        "images": images,
        "links": {
            "internal": internal,
            "external": external,
            "broken": broken
        },
        "canonical": canonical,
        "robots": robots,
        "sitemap": sitemap,
        "schemas": schemas,
        "speed": speed,
        "suggestions": suggestions,
        "score": score
    }

    # ===========================
    # BUILD TEXT OUTPUT
    # ===========================
    issues = []
    tips = []
    strengths = []

    # Title
    if not title:
        issues.append("Missing title tag.")
        tips.append("Add a descriptive and SEO-friendly title.")
    else:
        strengths.append("Title tag found.")

    # Meta
    if not meta:
        issues.append("Missing meta description.")
        tips.append("Add a meta description around 120–155 chars.")

    # H1
    if len(h1s) == 0:
        issues.append("Missing H1 tag.")
        tips.append("Add a clear primary H1 heading.")
    elif len(h1s) > 1:
        issues.append("Multiple H1 tags detected.")
        tips.append("Use only one H1 per page.")
    else:
        strengths.append("Proper H1 structure found.")

    # Density
    if density < 0.3:
        tips.append("Keyword density is low. Add keyword to content.")
    elif density > 3:
        tips.append("Keyword density is high. Reduce keyword usage.")

    # Word count
    wc = len(text.split())
    if wc < 300:
        tips.append("Content is thin. Increase to 600+ words.")

    # Images
    if images["missing_alt"] > 0:
        issues.append(f"{images['missing_alt']} images missing ALT text.")
        tips.append("Add ALT attributes for all images.")

    # Broken links
    if len(broken) > 0:
        issues.append(f"{len(broken)} broken links detected.")
        tips.append("Fix or remove broken links.")

    # Canonical
    if not canonical:
        tips.append("Add a canonical tag to avoid duplicate content issues.")

    # Schema
    if len(schemas) == 0:
        tips.append("Add schema markup for richer search results.")

    audit_text = "ISSUES:\n" + "\n".join(f"- {i}" for i in issues)
    tips_text = "TIPS:\n" + "\n".join(f"- {t}" for t in tips)

    return score, audit_text, tips_text, suggestions, json_output
