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
# INTERNAL HELPER – SAFE CHAT COMPLETION CALL
# ---------------------------------------------------
def ask_openai(prompt, model="gpt-4.1-mini"):
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an SEO expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        return response["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print("OpenAI error:", e)
        return "Error: AI request failed."


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
        Return ONLY the keyword.

        CONTENT:
        {text[:4000]}
        """

        return ask_openai(prompt, model="gpt-4.1-mini")

    except Exception as e:
        print("Keyword detection error:", e)
        return None


# ---------------------------------------------------
# KEYWORD SUGGESTIONS (5 keywords)
# ---------------------------------------------------
def generate_keyword_suggestions(url):
    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ")

        prompt = f"""
        List 5 strong SEO keywords this page could rank for.
        Return ONLY the keywords, 1 per line, no numbers.

        CONTENT:
        {text[:4000]}
        """

        result = ask_openai(prompt, model="gpt-4.1-mini")
        return [s.strip("•- ").strip() for s in result.split("\n") if s.strip()]

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

    return {"title": title, "meta": meta}


# ---------------------------------------------------
# MAIN SEO ANALYSIS PIPELINE
# ---------------------------------------------------
def run_seo_analysis(url, keyword):
    if not keyword:
        keyword = "general keyword"

    prompt = f"""
    Perform an SEO audit for:

    URL: {url}
    Keyword: {keyword}

    Provide:

    1. Keyword Score (0–100)
    2. Site Audit (issues + strengths)
    3. Optimization Tips

    Respond in clean, plain text.
    """

    output = ask_openai(prompt, model="gpt-4.1")

    return (
        f"Keyword Score for '{keyword}':\n{output[:200]}",
        "Site Audit:\n" + output,
        "Optimization Tips:\n" + output
    )
