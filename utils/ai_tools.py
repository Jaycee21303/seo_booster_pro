import os
from openai import OpenAI
from utils.db import fetch_one

# ---------------------------------------------------
# GET USER API KEY
# ---------------------------------------------------
def get_user_api_key(user_id):
    user = fetch_one("SELECT api_key FROM users WHERE id=%s", (user_id,))
    if not user or not user["api_key"]:
        return None
    return user["api_key"]


# ---------------------------------------------------
# GENERATE SEO TITLE
# ---------------------------------------------------
def generate_title(url, user_id):
    api_key = get_user_api_key(user_id)
    if not api_key:
        return "⚠️ No API key found. Add your OpenAI key in Settings."

    client = OpenAI(api_key=api_key)

    prompt = f"Write an optimized SEO page title for this website: {url}. Keep it under 60 characters."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI Error: {str(e)}"


# ---------------------------------------------------
# GENERATE META DESCRIPTION
# ---------------------------------------------------
def generate_meta(url, user_id):
    api_key = get_user_api_key(user_id)
    if not api_key:
        return "⚠️ No API key found. Add your OpenAI key in Settings."

    client = OpenAI(api_key=api_key)

    prompt = (
        f"Write an SEO-focused meta description for this website: {url}. "
        "Keep it under 155 characters and make it click-worthy."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI Error: {str(e)}"


# ---------------------------------------------------
# GENERATE KEYWORDS
# ---------------------------------------------------
def generate_keywords(url, user_id):
    api_key = get_user_api_key(user_id)
    if not api_key:
        return "⚠️ No API key found. Add your OpenAI key in Settings."

    client = OpenAI(api_key=api_key)

    prompt = (
        f"Generate a list of 10 high-value SEO keywords for the website: {url}. "
        "Return them in a simple comma-separated list."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI Error: {str(e)}"


# ---------------------------------------------------
# REWRITE HOMEPAGE CONTENT
# ---------------------------------------------------
def rewrite_homepage(url, user_id):
    api_key = get_user_api_key(user_id)
    if not api_key:
        return "⚠️ No API key found. Add your OpenAI key in Settings."

    client = OpenAI(api_key=api_key)

    prompt = (
        f"Rewrite the homepage content for this site: {url}. "
        "Keep the structure clear, improve readability, and make it SEO friendly. "
        "Avoid sounding robotic."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI Error: {str(e)}"
