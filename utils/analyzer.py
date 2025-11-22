import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------
# ANALYZE WEBSITE (title + meta)
# ---------------------------------------------------
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
