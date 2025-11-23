import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os

# -----------------------------------------------
# OPENAI CLIENT
# -----------------------------------------------
OPENAI_KEY = os.environ.get("OPENAI_KEY")
client = OpenAI(api_key=OPENAI_KEY)


# -----------------------------------------------
# AUTO-DETECT PRIMARY KEYWORD FROM PAGE
# -----------------------------------------------
def detect_keywords_from_page(url):
    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ")

        prompt = f"""
        Extract the single most important SEO keyword for this webpage.
        Return only the keyword. No punctuation. No description.

        PAGE CONTENT:
        {text[:4000]}
        """

        res = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        return res.output_text.strip()

    except Exception as e:
        print("Keyword detection error:", e)
        return None


# -----------------------------------------------
# GENERATE KEYWORD SUGGESTIONS (5 keywords)
# -----------------------------------------------
def generate_keyword_suggestions(url):
    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ")

        prompt = f"""
        Analyze this webpage and list the 5 strongest SEO keywords
        it could realistically rank for.

        Return ONLY the keywords.
        No numbers. No bullets. No explanations.

        PAGE CONTENT:
        {text[:4000]}
        """

        res = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        # Split into list
        suggestions = res.output_text.strip().split("\n")
        return [s.strip("•- ").strip() for s in suggestions if s.strip()]

    except Exception as e:
        print("Keyword suggestion error:", e)
        return []


# -----------------------------------------------
# URL TITLE + META EXTRACTION
# -----------------------------------------------
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

    return {"title": title, "meta": meta}


# -----------------------------------------------
# MAIN AI SEO ANALYSIS PIPELINE
# -----------------------------------------------
def run_seo_analysis(url, keyword):
    """
    Returns:
      keyword_score       – relevance score
      site_audit          – list of issues + strengths
      optimization_tips   – list of improvement tips
    """

    # Safety fallback
    if not keyword:
        keyword = "general keyword"

    prompt = f"""
    You are an expert SEO auditor.

    TASK:
    Analyze the website URL: {url}
    Target keyword: {keyword}

    Produce the following:

    1. KEYWORD SCORE (0-100)
       How well this page ranks for the keyword.

    2. SITE AUDIT
       - Missing SEO elements
       - Page weaknesses
       - Technical issues
       - On-page issues

    3. OPTIMIZATION TIPS
       - Specific actions to improve ranking
       - Keyword placement suggestions
       - Meta + title recommendations

    Respond in clean text, NOT JSON.
    """

    res = client.responses.create(
        model="gpt-4.1",
        input=prompt
    )

    output = res.output_text

    # For now, return raw text in sections
    # (Can be upgraded later to structured output)
    return (
        f"Keyword Match Score for '{keyword}':\n" + output[:200],  # truncated section
        "Site Audit:\n" + output,
        "Optimization Tips:\n" + output
    )
