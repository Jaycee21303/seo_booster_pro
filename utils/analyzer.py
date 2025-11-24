import requests
from bs4 import BeautifulSoup
from collections import Counter
import re
import math


# ---------------------------------------------------
# TEXT CLEANING
# ---------------------------------------------------
def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------------------------------------------------
# FETCH + PARSE PAGE
# ---------------------------------------------------
def fetch_page(url):
    try:
        response = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0"
        })
        if response.status_code != 200:
            return None, None

        soup = BeautifulSoup(response.text, "html.parser")
        return response.text, soup

    except:
        return None, None


# ---------------------------------------------------
# TF-IDF KEYWORD MODELING (AI-like local logic)
# ---------------------------------------------------
def keyword_extract(text, top_n=10):
    words = clean_text(text).split()
    total = len(words)

    if total == 0:
        return []

    freq = Counter(words)
    scores = {}

    # compute tf-idf-like heuristic score
    for word, count in freq.items():
        if len(word) < 4:
            continue
        tf = count / total
        idf = math.log(1 + (total / (count + 1)))
        scores[word] = tf * idf

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [w for w, s in ranked[:top_n]]


# ---------------------------------------------------
# BROKEN LINK CHECK
# ---------------------------------------------------
def check_broken_links(url, soup):
    broken = []
    links = soup.find_all("a")

    for link in links:
        href = link.get("href")

        if not href or href.startswith("#") or href.startswith("mailto"):
            continue

        if href.startswith("/"):
            base = url.rstrip("/")
            href = base + href

        try:
            r = requests.get(href, timeout=5)
            if r.status_code >= 400:
                broken.append(href)
        except:
            broken.append(href)

        if len(broken) >= 20:  # safety cap
            break

    return broken


# ---------------------------------------------------
# STRUCTURAL SEO CHECKS
# ---------------------------------------------------
def structural_audit(soup):
    findings = []

    # Title
    title = soup.find("title")
    if not title or len(title.text.strip()) == 0:
        findings.append("❌ Missing or empty <title> tag.")
    else:
        t = title.text.strip()
        if len(t) < 20:
            findings.append("⚠️ Title too short (<20 chars).")
        elif len(t) > 70:
            findings.append("⚠️ Title too long (>70 chars).")
        else:
            findings.append("✅ Title length looks good.")

    # Meta description
    meta = soup.find("meta", attrs={"name": "description"})
    if not meta or not meta.get("content"):
        findings.append("❌ Missing meta description.")
    else:
        desc = meta["content"]
        if len(desc) < 50:
            findings.append("⚠️ Meta description too short.")
        elif len(desc) > 160:
            findings.append("⚠️ Meta description too long.")
        else:
            findings.append("✅ Meta description length is good.")

    # H1 tags
    h1s = soup.find_all("h1")
    if len(h1s) == 0:
        findings.append("❌ Missing H1 tag.")
    elif len(h1s) > 1:
        findings.append("⚠️ Multiple H1 tags found.")
    else:
        findings.append("✅ H1 structure looks good.")

    # Image alt tags
    imgs = soup.find_all("img")
    missing_alt = sum(1 for img in imgs if not img.get("alt"))
    if missing_alt > 0:
        findings.append(f"⚠️ {missing_alt} images missing alt text.")
    else:
        findings.append("✅ All images have alt attributes.")

    # Schema
    if soup.find("script", type="application/ld+json"):
        findings.append("✅ Structured data detected (JSON-LD).")
    else:
        findings.append("⚠️ No structured data detected.")

    # Mobile meta tag
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if viewport:
        findings.append("✅ Mobile-friendly viewport tag detected.")
    else:
        findings.append("⚠️ Missing mobile viewport tag.")

    return findings


# ---------------------------------------------------
# KEYWORD RELEVANCE SCORING
# ---------------------------------------------------
def keyword_relevance_score(keyword, text):
    if not keyword:
        return 50  # neutral score

    text = clean_text(text)
    words = text.split()

    if len(words) == 0:
        return 20

    count = words.count(keyword.lower())
    density = count / len(words)

    score = min(100, int(density * 20000))
    return score


# ---------------------------------------------------
# AI-STYLE OPTIMIZATION TIPS (6–10 bullet points)
# ---------------------------------------------------
def generate_ai_style_tips(soup, keyword):
    tips = []

    title = soup.find("title").text.strip() if soup.find("title") else ""

    if not keyword:
        tips.append("• Consider focusing on one primary keyword to strengthen topical relevance.")
    else:
        tips.append(f"• Include your main keyword “{keyword}” naturally in the title, meta description, and H1.")

    if len(title) < 40:
        tips.append("• Expand your title to improve click-through rate and provide more context to search engines.")

    if not soup.find("meta", attrs={"name": "description"}):
        tips.append("• Add a compelling meta description with a clear value proposition.")
    else:
        tips.append("• Improve your meta description to increase engagement and SERP performance.")

    if len(soup.find_all("h2")) < 2:
        tips.append("• Add more H2 subheadings to structure your content better.")

    if soup.find("script", type="application/ld+json") is None:
        tips.append("• Implement structured data (JSON-LD) to enhance how search engines understand your page.")

    imgs = soup.find_all("img")
    if any(not img.get("alt") for img in imgs):
        tips.append("• Ensure all images have descriptive alt text for accessibility and SEO.")

    if len(tips) < 6:
        tips.append("• Expand your content with more semantically related terms and supporting keywords.")

    if len(tips) < 8:
        tips.append("• Improve internal linking to help distribute authority and guide users.")

    if len(tips) < 10:
        tips.append("• Optimize page load speed by compressing images and deferring non-critical scripts.")

    return "\n".join(tips)


# ---------------------------------------------------
# MAIN ENTRY POINT FOR APP: run_local_seo_analysis()
# ---------------------------------------------------
def run_local_seo_analysis(url, keyword=None):
    html, soup = fetch_page(url)
    if not soup:
        return 0, "Error fetching page.", "Unable to analyze page."

    text = soup.get_text(separator=" ")
    text_clean = clean_text(text)

    # extract top keywords
    extracted_keywords = keyword_extract(text_clean)

    # structural findings
    structure = structural_audit(soup)

    # broken links
    broken = check_broken_links(url, soup)

    # keyword relevance
    score_keyword = keyword_relevance_score(keyword, text_clean)

    # combined score (simple heuristic)
    score = int(
        score_keyword * 0.4
        + (100 - min(len(broken) * 5, 50)) * 0.3
        + (len([x for x in structure if x.startswith("✅")]) / len(structure)) * 100 * 0.3
    )

    score = max(5, min(100, score))

    # build audit text
    audit_text = "STRUCTURAL AUDIT:\n" + "\n".join(structure)
    audit_text += "\n\nBROKEN LINKS:\n"
    audit_text += "\n".join(broken) if broken else "No broken links detected."
    audit_text += "\n\nKEYWORDS DETECTED:\n" + ", ".join(extracted_keywords)

    # AI-style tips
    tips = generate_ai_style_tips(soup, keyword)

    return score, audit_text, tips
