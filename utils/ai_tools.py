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
# CALL OPENAI CHAT COMPLETIONS
# -----------------------------------
def call_ai(prompt, user_id):
    api_key = get_api_key(user_id)

    if not api_key:
        return "⚠️ No API key found. Please add your API key in Settings."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        r = requests.post(OPENAI_API_URL, headers=headers, json=data)
        r_json = r.json()
        return r_json["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI Error: {str(e)}"


# -----------------------------------
# AI TOOLS IMPLEMENTATION
# -----------------------------------

def generate_title(url, user_id):
    prompt = f"""
    You are an expert SEO consultant.
    Generate 5 powerful, high-CTR, SEO-optimized page titles for the website:

    {url}

    Return only the titles, no explanation.
    """
    return call_ai(prompt, user_id)


def generate_meta(url, user_id):
    prompt = f"""
    Write 3 strong SEO meta descriptions for:

    {url}

    Each one should be 150–160 characters max and optimized for click-through.
    """
    return call_ai(prompt, user_id)


def rewrite_homepage(url, user_id):
    prompt = f"""
    Rewrite the homepage content of {url} to be clean, professional, 
    keyword-rich, and optimized for SEO.
    Make the tone clear, concise, and conversion-focused.

    Return only the improved homepage content.
    """
    return call_ai(prompt, user_id)


def keyword_list(url, country, user_id):
    prompt = f"""
    Generate a list of 15 SEO keywords for {url} targeted for users in {country}.

    Include:
    - High-intent keywords
    - Localized keywords
    - Long-tail keywords
    """
    return call_ai(prompt, user_id)
