from flask import Flask, render_template, request, redirect, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, datetime

from utils.analyzer import analyze_website
from utils.ai_tools import generate_title, generate_meta, rewrite_homepage, keyword_list
from utils.pdf_generator import create_pdf_report

app = Flask(__name__)
app.secret_key = "CHANGE_THIS"

def init_db():
    if not os.path.exists("database.db"):
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("""CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT,
            api_key TEXT,
            date_created TEXT
        )""")
        conn.commit()
        conn.close()
init_db()

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    def wrapper(*a, **k):
        if "user_id" not in session:
            return redirect("/login")
        return f(*a, **k)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route("/")
def home():
    return redirect("/login")

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method=="POST":
        email=request.form["email"].lower()
        pw=request.form["password"]
        conn=get_db()
        c=conn.cursor()
        try:
            hashed=generate_password_hash(pw)
            c.execute("INSERT INTO users(email,password,date_created) VALUES(?,?,?)",
                      (email,hashed,str(datetime.datetime.now())))
            conn.commit()
            c.execute("SELECT id FROM users WHERE email=?", (email,))
            u=c.fetchone()
            conn.close()
            session["user_id"]=u["id"]
            session["email"]=email
            return redirect("/dashboard")
        except:
            conn.close()
            return render_template("signup.html",error="Email exists.")
    return render_template("signup.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form["email"].lower()
        pw=request.form["password"]
        conn=get_db()
        c=conn.cursor()
        c.execute("SELECT * FROM users WHERE email=?", (email,))
        u=c.fetchone()
        conn.close()
        if u and check_password_hash(u["password"],pw):
            session["user_id"]=u["id"]
            session["email"]=u["email"]
            return redirect("/dashboard")
        return render_template("login.html",error="Invalid login.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/dashboard",methods=["GET","POST"])
@login_required
def dashboard():
    url=""
    results=None
    if request.method=="POST":
        url=request.form["url"]
        results=analyze_website(url)
    return render_template("dashboard.html", url=url, results=results)

@app.route("/settings",methods=["GET","POST"])
@login_required
def settings():
    conn=get_db()
    c=conn.cursor()
    if request.method=="POST":
        k=request.form["api_key"]
        c.execute("UPDATE users SET api_key=? WHERE id=?", (k,session["user_id"]))
        conn.commit()
    c.execute("SELECT api_key FROM users WHERE id=?", (session["user_id"],))
    row=c.fetchone()
    api_key=row["api_key"] if row and row["api_key"] else ""
    conn.close()
    return render_template("settings.html", api_key=api_key)

@app.route("/ai/title",methods=["POST"])
@login_required
def ai_title():
    return generate_title(request.form["analyze_url"], session["user_id"])

@app.route("/ai/meta",methods=["POST"])
@login_required
def ai_meta():
    return generate_meta(request.form["analyze_url"], session["user_id"])

@app.route("/ai/rewrite",methods=["POST"])
@login_required
def ai_rewrite():
    return rewrite_homepage(request.form["analyze_url"], session["user_id"])

@app.route("/ai/keywords",methods=["POST"])
@login_required
def ai_keywords():
    return keyword_list(request.form["analyze_url"], session["user_id"])

@app.route("/download_report",methods=["POST"])
@login_required
def download_report():
    f=create_pdf_report(request.form["report_data"])
    return send_file(f, as_attachment=True)

if __name__=="__main__":
    app.run(debug=True)
