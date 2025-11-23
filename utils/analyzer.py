import requests
from bs4 import BeautifulSoup
import openai
import os

# ---------------------------------------------------
# OPENAI KEY SETUP
# ---------------------------------------------------
OPENAI_KEY = os.environ.get("OPENAI_KEY")
openai.api_key = OPENAI_KEY


# ---------------------------------------------------
# AUTO-DETECT PRIMARY KEYWORD
# ---------------------------------------------------
def detect_keywords_from_page(url):
    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ")

        prompt = f"""
        Extract the single most important SEO keyword from this webpage.
        Return ONLY the keyword, no punctuation.

        CONTENT:
        {text[:4000]}
        """

        res = openai.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        return res.output_text.strip()

    except Exception as e:
        print("Keyword detection error:", e)
        return None


# ---------------------------------------------------
# KEYWORD SUGGESTIONS
# ---------------------------------------------------
def generate_keyword_suggestions(url):
    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ")

        prompt = f"""
        List 5 strong SEO keywords this page could rank for.
        Only output the keywords. No numbering.

        CONTENT:
        {text[:4000]}
        """

        res = openai.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        suggestions = res.output_text.strip().split("\n")
        return [s.strip("•- ").strip() for s in suggestions if s.strip()]

    except Exception as e:
        print("Keyword suggestion error:", e)
        return []


# ---------------------------------------------------
# BASIC ON-PAGE ANALYSIS
# ---------------------------------------------------
def analyze_url(url):
    try:
        response = requests.get(url, timeout=8)
    except Exception as e:
        return {"error": f"Could not reach URL: {str(e)}"}

    if response.status_code != 200:
        return {"error": f"URL responded with status code {response.status_code}"}

    soup = BeautifulSoup(response.text, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.text.strip() if title_tag else "No title found"

    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta = meta_tag["content"].strip() if meta_tag and "content" in meta_tag.attrs else "No meta description found"

    return {
        "title": title,
        "meta": meta,
    }


# ---------------------------------------------------
# MAIN SEO ANALYSIS
# ---------------------------------------------------
def run_seo_analysis(url, keyword):
    if not keyword:
        keyword = "general keyword"

    prompt = f"""
    Perform an SEO audit for:

    URL: {url}
    Keyword: {keyword}

    Provide:

    1. Keyword Score (0-100)
    2. Site Audit (issues + strengths)
    3. Optimizations Tips

    Clear, simple text only.
    """

    res = openai.responses.create(
        model="gpt-4.1",
        input=prompt
    )

    output = res.output_text

    return (
        f"Keyword Score for '{keyword}':\n" + output[:200],
        "Site Audit:\n" + output,
        "Optimization Tips:\n" + output
    )
