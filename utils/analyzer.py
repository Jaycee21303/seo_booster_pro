import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os

# ---------------------------------------------------
# OpenAI client (new SDK)
# ---------------------------------------------------
OPENAI_KEY = os.environ.get("OPENAI_KEY")
client = OpenAI(api_key=OPENAI_KEY)


# ---------------------------------------------------
# SAFE OPENAI CALL
# ---------------------------------------------------
def ask_openai(prompt, model="gpt-4o-mini"):
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
# Extract text safely
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
# Keyword detection
# ---------------------------------------------------
def detect_keywords_from_page(url):
    text = extract_page_text(url)
    if not text:
        return None

    prompt = f"""
    Extract the main target SEO keyword from this content.
    Return ONLY the keyword.

    Content:
    {text}
    """

    result = ask_openai(prompt)
    return result if result else None


# ---------------------------------------------------
# Keyword suggestions
# ---------------------------------------------------
def generate_keyword_suggestions(url):
    text = extract_page_text(url)
    if not text:
        return []

    prompt = f"""
    Provide 5 SEO keywords this page could rank for.
    ONE KEYWORD PER LINE.
    """

    result = ask_openai(prompt)
    if not result:
        return []

    return [k.strip() for k in result.split("\n") if k.strip()]


# ---------------------------------------------------
# Main SEO analysis
# ---------------------------------------------------
def run_seo_analysis(url, keyword):
    if not keyword:
        keyword = "general topic"

    prompt = f"""
    Perform an SEO analysis.

    URL: {url}
    Keyword: {keyword}

    Return EXACTLY this structure:

    SCORE: <0-100>
    AUDIT:
    - Issue or strength
    - Issue or strength
    TIPS:
    - Tip
    - Tip
    """

    output = ask_openai(prompt, model="gpt-4o")
    if not output:
        return 0, "AI request failed.", "AI request failed."

    # -------------------------------
    # Parse structured output
    # -------------------------------
    score = 50
    audit = ""
    tips = ""
    section = None

    for line in output.split("\n"):
        line = line.strip()

        if line.startswith("SCORE:"):
            try:
                score = int(line.replace("SCORE:", "").strip())
            except:
                score = 50

        elif line.startswith("AUDIT:"):
            section = "audit"

        elif line.startswith("TIPS:"):
            section = "tips"

        else:
            if section == "audit":
                audit += line + "\n"
            elif section == "tips":
                tips += line + "\n"

    return score, audit.strip(), tips.strip()
