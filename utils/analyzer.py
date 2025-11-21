import requests
from bs4 import BeautifulSoup

def analyze_website(url):

    # ------------------------
    # FETCH WEBSITE HTML
    # ------------------------
    try:
        response = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        html = response.text
    except Exception as e:
        return {
            "score": 0,
            "issues": [f"Could not reach website: {str(e)}"]
        }

    soup = BeautifulSoup(html, "html.parser")
    issues = []
    score = 100


    # ------------------------
    # TITLE TAG
    # ------------------------
    title_tag = soup.title.string if soup.title else None
    if not title_tag:
        issues.append("Missing title tag.")
        score -= 15


    # ------------------------
    # META DESCRIPTION
    # ------------------------
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if not meta_desc or not meta_desc.get("content"):
        issues.append("Missing meta description.")
        score -= 10


    # ------------------------
    # H1 TAG
    # ------------------------
    h1_tag = soup.find("h1")
    if not h1_tag:
        issues.append("Missing H1 tag.")
        score -= 10


    # ------------------------
    # IMG ALT TEXT CHECK
    # ------------------------
    images = soup.find_all("img")
    missing_alt = [img for img in images if not img.get("alt")]

    if len(missing_alt) > 0:
        issues.append(f"{len(missing_alt)} images missing alt text.")
        score -= 10


    # ------------------------
    # CONTENT WORD COUNT
    # ------------------------
    text = soup.get_text(separator=" ")
    word_count = len(text.split())

    if word_count < 300:
        issues.append("Very low content (under 300 words).")
        score -= 10


    # ------------------------
    # KEYWORD ALIGNMENT (TITLE ↔ BODY)
    # ------------------------
    if title_tag:
        title_words = title_tag.lower().split()
        body_words = text.lower().split()
        match_count = sum(1 for word in title_words if word in body_words)

        if match_count < 2:
            issues.append("Page title is not aligned with body keywords.")
            score -= 5


    # ------------------------
    # FINAL SCORE NORMALIZATION
    # ------------------------
    if score < 0:
        score = 0
    if score > 100:
        score = 100

    return {
        "score": score,
        "issues": issues
    }
