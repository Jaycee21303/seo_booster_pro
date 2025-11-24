import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os

# ---------------------------------------------------
# OPENAI CLIENT
# ---------------------------------------------------
OPENAI_KEY = os.environ.get("OPENAI_KEY")
client = OpenAI(api_key=OPENAI_KEY)


# ---------------------------------------------------
# SAFE CALL TO OPENAI
# ---------------------------------------------------
def ask_openai(prompt, model="gpt-4.1-mini"):
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an SEO expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        return completion.choices[0].message.content.strip()

    except Exception as e:
        print("OpenAI Error:", e)
        return None


# ---------------------------------------------------
# EXTRACT CLEAN TEXT FROM URL (LIMIT 3000 CHARS)
# ---------------------------------------------------
def extract_page_text(url):
    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ")
        return text[:3000]

    except:
        return ""


# ---------------------------------------------------
# AUTO-KEYWORD DETECTION
# ---------------------------------------------------
def detect_keywords_from_page(url):
    text = extract_page_text(url)
    if not text:
        return None

    prompt = f"""
    From the following webpage text, extract the SINGLE best SEO keyword.
    Return ONLY the keyword.

    Content:
    {text}
    """

    result = ask_openai(prompt)
    return result if result else None


# ---------------------------------------------------
# KEYWORD SUGGESTIONS
# ---------------------------------------------------
def generate_keyword_suggestions(url):
    text = extract_page_text(url)
    if not text:
        return []

    prompt = f"""
    Suggest the 5 best SEO keywords this page could rank for.
    Return ONLY keywords, one per line, no numbering.

    Content:
    {text}
    """

    result = ask_openai(prompt)
    if not result:
        return []

    return [k.strip("•- ").strip() for k in result.split("\n") if k.strip()]


# ---------------------------------------------------
# MAIN SEO ANALYSIS (PROPER OUTPUT FORMAT)
# ---------------------------------------------------
def run_seo_analysis(url, keyword):
    if not keyword:
        keyword = "general topic"

    prompt = f"""
    Perform an SEO analysis for the following:

    URL: {url}
    Target Keyword: {keyword}

    Provide results using this EXACT format:

    SCORE: <number 0-100>
    AUDIT:
    <2-4 bullet points about issues + strengths>
    TIPS:
    <2-4 bullet points of improvements>
    """

    response = ask_openai(prompt, model="gpt-4.1")
    if not response:
        return 0, "AI request failed.", "AI request failed."

    # -------------------------------
    # PARSE RESPONSE CLEANLY
    # -------------------------------
    score = 0
    audit = ""
    tips = ""

    lines = response.split("\n")

    current_section = None

    for line in lines:
        line = line.strip()

        # SCORE
        if line.startswith("SCORE:"):
            num = line.replace("SCORE:", "").strip()
            try:
                score = int(num)
            except:
                score = 50  # fallback

        # AUDIT section begins
        elif line.startswith("AUDIT:"):
            current_section = "audit"
            continue

        # TIPS section begins
        elif line.startswith("TIPS:"):
            current_section = "tips"
            continue

        else:
            if current_section == "audit":
                audit += line + "\n"
            if current_section == "tips":
                tips += line + "\n"

    # FINAL CLEAN
    audit = audit.strip() or "No audit data."
    tips = tips.strip() or "No tips available."

    # Guarantee score is valid integer
    if score < 0 or score > 100:
        score = 50

    return score, audit, tips
