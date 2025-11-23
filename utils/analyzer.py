import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------
# ANALYZE WEBSITE (title + meta)
# ---------------------------------------------------
def detect_keywords_from_page(url):
    import requests
    from bs4 import BeautifulSoup
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_KEY)

    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ")

        prompt = f"""
        Extract the single most important SEO keyword for this webpage.
        Return only the keyword, nothing else.

        Page text:
        {text[:4000]}
        """

        res = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        return res.output_text.strip()

    except:
        return None

def analyze_url(url):
    try:
        response = requests.get(url, timeout=8)
    except Exception as e:
        return {"error": f"Could not reach URL: {str(e)}"}

    if response.status_code != 200:
        return {"error": f"URL responded with status code {response.status_code}"}

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract title
    title_tag = soup.find("title")
    title = title_tag.text.strip() if title_tag else "No title found"

    # Extract meta description
    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta = meta_tag["content"].strip() if meta_tag and "content" in meta_tag.attrs else "No meta description found"

    # Placeholder screenshot (optional upgrade later)
    screenshot_placeholder = "Screenshot feature coming soon."

    return {
        "title": title,
        "meta": meta,
        "screenshot": screenshot_placeholder
    }
def generate_keyword_suggestions(url):
    import requests
    from bs4 import BeautifulSoup
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_KEY)

    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ")

        prompt = f"""
        Analyze this webpage and list 5 strong SEO keywords it could rank for.
        Return only the list, no descriptions, no numbers.
        Text:
        {text[:4000]}
        """

        res = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        suggestions = res.output_text.strip().split("\n")
        return [s.strip("•- ") for s in suggestions if s.strip()]

    except:
        return []
