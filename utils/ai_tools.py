import sqlite3
import requests

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

def get_api_key(user_id):
    conn=sqlite3.connect("database.db")
    c=conn.cursor()
    c.execute("SELECT api_key FROM users WHERE id=?", (user_id,))
    row=c.fetchone()
    conn.close()
    return row[0] if row else None

def call_ai(prompt,user_id):
    key=get_api_key(user_id)
    if not key:
        return "⚠️ No API key found."
    headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"}
    data={'model':'gpt-4o-mini','messages':[{'role':'system','content':'You are an expert SEO assistant.'},{'role':'user','content':prompt}],'temperature':0.7}
    r=requests.post(OPENAI_API_URL,json=data,headers=headers)
    j=r.json()
    try: return j['choices'][0]['message']['content']
    except: return str(j)

def generate_title(url,u): return call_ai(f"Generate 5 high-CTR SEO titles for {url}.",u)
def generate_meta(url,u): return call_ai(f"Generate 3 SEO meta descriptions for {url}.",u)
def rewrite_homepage(url,u): return call_ai(f"Rewrite homepage content for {url}.",u)
def keyword_list(url,u): return call_ai(f"Generate 15 SEO keywords for {url} with no countries.",u)
