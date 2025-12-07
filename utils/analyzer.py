import requests
from bs4 import BeautifulSoup
from collections import Counter
import re
import math


# ---------------------------------------------------
# BASIC TEXT CLEANING
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
# TF-IDF SEMANTIC KEYWORD MODELING
# ---------------------------------------------------
def extract_semantic_phrases(text, top_n=15):
    words = clean_text(text).split()
    if len(words) < 20:
        return []

    freq = Counter(words)
    total = len(words)

    scores = {}
    for w, c in freq.items():
        if len(w) < 4:
            continue
        tf = c / total
        idf = math.log(1 + (total / (c + 1)))
        scores[w] = tf * idf

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [x[0] for x in ranked[:top_n]]


# ---------------------------------------------------
# READABILITY SCORE (Flesch-like heuristic)
# ---------------------------------------------------
def readability_score(text):
    words = text.split()
    if len(words) == 0:
        return 30

    sentences = max(1, text.count('.') + text.count('!') + text.count('?'))
    syllables = sum(len(re.findall(r"[aeiouy]+", w)) for w in words)

    wps = len(words) / sentences
    spw = syllables / len(words)

    # Simplified readability scoring (0–100)
    score = 100 - (wps * 5) - (spw * 20)
    return max(5, min(95, int(score)))


# ---------------------------------------------------
# HEADING STRUCTURE SCORE
# ---------------------------------------------------
def heading_structure_score(soup):
    h1 = soup.find_all("h1")
    h2 = soup.find_all("h2")
    h3 = soup.find_all("h3")

    score = 0

    # H1 rules
    if len(h1) == 1:
        score += 30
    elif len(h1) > 1:
        score += 5
    else:
        score += 0

    # H2 presence
    if len(h2) >= 2:
        score += 30
    elif len(h2) == 1:
        score += 15

    # H3 depth
    if len(h3) >= 2:
        score += 20
    elif len(h3) == 1:
        score += 10

    # Max = 80 → scale to 100
    return min(100, int(score * 1.25))


# ---------------------------------------------------
# BROKEN LINK CHECK (up to 20)
# ---------------------------------------------------
def link_health_score(url, soup):
    links = soup.find_all("a")
    broken = 0
    checked = 0

    for link in links:
        href = link.get("href")
        if not href or href.startswith("#") or href.startswith("mailto"):
            continue

        if href.startswith("/"):
            href = url.rstrip("/") + href

        try:
            r = requests.get(href, timeout=5)
            if r.status_code >= 400:
                broken += 1
        except:
            broken += 1

        checked += 1
        if checked >= 20:
            break

    if checked == 0:
        return 70  # neutral

    good_ratio = (checked - broken) / checked
    return int(good_ratio * 100)


# ---------------------------------------------------
# TECHNICAL HEALTH SCORE
# ---------------------------------------------------
def technical_score(soup):
    score = 0

    # Meta description
    meta = soup.find("meta", attrs={"name": "description"})
    if meta:
        md = meta.get("content", "")
        if 50 <= len(md) <= 160:
            score += 20
        else:
            score += 10

    # Viewport tag (mobile)
    if soup.find("meta", attrs={"name": "viewport"}):
        score += 20

    # Schema / JSON-LD
    if soup.find("script", type="application/ld+json"):
        score += 20

    # Title rules
    title = soup.find("title")
    if title:
        t = title.text.strip()
        if 20 <= len(t) <= 70:
            score += 20
        else:
            score += 10

    # Image alt text ratio
    imgs = soup.find_all("img")
    if imgs:
        with_alt = sum(1 for img in imgs if img.get("alt"))
        ratio = with_alt / len(imgs)
        score += int(ratio * 20)
    else:
        score += 10

    return min(100, score)


# ---------------------------------------------------
# KEYWORD RELEVANCE SCORE
# ---------------------------------------------------
def keyword_relevance(keyword, text):
    if not keyword:
        return 60  # neutral

    words = clean_text(text).split()
    if len(words) == 0:
        return 30

    density = words.count(keyword.lower()) / len(words)
    score = min(100, int(density * 30000))
    return max(5, score)


# ---------------------------------------------------
# AI-STYLE OPTIMIZATION TIPS
# ---------------------------------------------------
def generate_tips(soup, keyword):
    tips = []

    if keyword:
        tips.append(f"• Use your target keyword “{keyword}” in the title, H1, and early in the content.")
    tips.append("• Improve your meta description to better capture search intent.")
    tips.append("• Add more H2/H3 subheadings to improve structure and readability.")
    tips.append("• Expand your content with semantically related terms and supporting concepts.")
    tips.append("• Improve internal linking to help search engines understand your content.")
    tips.append("• Add descriptive alt text to all images.")
    tips.append("• Implement structured data (JSON-LD) for better SERP features.")
    tips.append("• Optimize page load speed by compressing images and minimizing scripts.")
    tips.append("• Ensure your page is mobile-friendly with responsive elements.")

    return "\n".join(tips)


# ---------------------------------------------------
# MAIN HYBRID-AI ANALYZER ENTRY POINT
# ---------------------------------------------------
def run_local_seo_analysis(url, keyword=None):
    html, soup = fetch_page(url)
    if not soup:
        return (
            0, "Error fetching page.", "Unable to analyze page.",
            0, 0, 0, 0, 0, {}
        )

    text = soup.get_text(separator=" ")
    text_clean = clean_text(text)

    # CONTENT SCORE (C3: combined)
    wc = len(text_clean.split())
    wc_score = min(100, int((wc / 800) * 100))  # word count target ~800

    sem_terms = extract_semantic_phrases(text_clean)
    sem_score = min(100, len(sem_terms) * 5)  # up to ~15 terms → 75

    read_score = readability_score(text)

    heading_score = heading_structure_score(soup)

    content_score = int((wc_score * 0.35) + (sem_score * 0.35) + (read_score * 0.15) + (heading_score * 0.15))

    # KEYWORD SCORE
    keyword_score_value = keyword_relevance(keyword, text_clean)

    # TECHNICAL SCORE
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    canonical_link = soup.find("link", rel="canonical") or soup.find("link", attrs={"rel": "canonical"})
    schema_present = bool(soup.find("script", type="application/ld+json"))
    viewport_present = bool(soup.find("meta", attrs={"name": "viewport"}))
    imgs = soup.find_all("img")
    if imgs:
        with_alt = sum(1 for img in imgs if img.get("alt"))
        alt_coverage = int((with_alt / len(imgs)) * 100)
    else:
        alt_coverage = None

    technical_score_value = technical_score(soup)

    # ON-PAGE SCORE (headings + meta balance)
    onpage_score = int((heading_score * 0.6) + ((100 if soup.find('meta', attrs={'name': 'description'}) else 50) * 0.4))

    # LINK SCORE
    link_score = link_health_score(url, soup)

    # MAIN SCORE (S2 content-heavy model)
    main_score = int(
        content_score * 0.40 +
        keyword_score_value * 0.25 +
        technical_score_value * 0.20 +
        onpage_score * 0.10 +
        link_score * 0.05
    )

    main_score = max(5, min(100, main_score))

    audit_text = (
        "CONTENT ANALYSIS:\n"
        f"- Word count score: {wc_score}\n"
        f"- Readability score: {read_score}\n"
        f"- Semantic richness score: {sem_score}\n"
        f"- Heading structure: {heading_score}\n\n"

        "KEYWORD ANALYSIS:\n"
        f"- Keyword relevance score: {keyword_score_value}\n\n"

        "TECHNICAL HEALTH:\n"
        f"- Technical score: {technical_score_value}\n\n"

        "ON-PAGE STRUCTURE:\n"
        f"- On-page score: {onpage_score}\n\n"

        "LINK HEALTH:\n"
        f"- Link score: {link_score}\n"
    )

    tips = generate_tips(soup, keyword)

    page_meta = {
        "title": soup.title.string.strip() if soup.title else "No title detected",
        "description": (
            meta_desc_tag.get("content", "") if meta_desc_tag else "No meta description detected"
        ),
        "word_count": wc,
        "top_terms": sem_terms[:6],
        "h1": [h.get_text(strip=True) for h in soup.find_all("h1")][:3],
        "readability_score": read_score,
        "schema_present": schema_present,
        "alt_coverage": alt_coverage,
        "canonical_url": canonical_link.get("href") if canonical_link else None,
        "title_length": len(soup.title.string.strip()) if soup.title and soup.title.string else 0,
        "description_length": len(meta_desc_tag.get("content", "")) if meta_desc_tag else 0,
        "h1_count": len(soup.find_all("h1")),
        "viewport_present": viewport_present,
    }

    return (
        main_score,
        audit_text,
        tips,
        content_score,
        technical_score_value,
        keyword_score_value,
        onpage_score,
        link_score,
        page_meta,
    )
