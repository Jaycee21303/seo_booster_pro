import sqlite3
import requests
import json

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


# -----------------------------------
# GET USER'S STORED API KEY
# -----------------------------------
def get_api_key(user_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT api_key FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


# -----------------------------------
# OPENAI CALL WRAPPER
# -----------------------------------
def call_ai(prompt, user_id):
    api_key = get_api_key(user_id)

    if not api_key:
        return "⚠️ No API key found. Please add your OpenAI API key in Settings."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are an expert SEO assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(OPENAI_API_URL, json=data, headers=headers)
        result = response.json()

        return result["choices"][0]["message"]["content"]

    except Exception as e:
        return f"❌ AI Error: {str(e)}"


# -----------------------------------
# AI TOOL FUNCTIONS
# -----------------------------------

def generate_title(url, user_id):
    prompt = f"""
    Generate 5 powerful, high-CTR SEO page titles for the website:

    {url}

    Make them:
    - Click-worthy
    - Under 60 characters
    - Professional
    - Conversion-focused

    Return only the list of titles.
    """
    return call_ai(prompt, user_id)


def generate_meta(url, user_id):
    prompt = f"""
    Create 3 SEO-optimized meta descriptions for:

    {url}

    Requirements:
    - 150–160 characters
    - High click-through rate
    - Clear and professional
    - Include strong keywords

    Return only the meta descriptions.
    """
    return call_ai(prompt, user_id)


def rewrite_homepage(url, user_id):
    prompt = f"""
    Rewrite the homepage content for:

    {url}

    Make it:
    - Clear and professional
    - Search-optimized
    - Readable and engaging
    - Keyword-rich
    - Persuasive

    Return only the improved homepage content.
    """
    return call_ai(prompt, user_id)


def keyword_list(url, user_id):
    prompt = f"""
    Generate a list of 15 strong SEO keywords for the website:

    {url}

    Include:
    - High-intent keywords
    - Long-tail keywords
    - Commercial keywords
    - No country names
    - No locations

    Return only the keyword list.
    """
    return call_ai(prompt, user_id)
