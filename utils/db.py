import psycopg2, psycopg2.extras, os

# -----------------------------
# CONNECT TO DATABASE
# -----------------------------
def get_conn():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        sslmode="require"
    )

# -----------------------------
# BASIC QUERY HELPERS
# -----------------------------
def fetch_one(query, params=()):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()
    return row


def fetch_all(query, params=()):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def execute(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    conn.close()


# -----------------------------
# AUTO-CREATE TABLES
# -----------------------------
def init_db():
    # USERS TABLE
    execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE,
        password TEXT,
        api_key TEXT,
        last_url TEXT,
        date_created TIMESTAMP DEFAULT NOW()
    );
    """)

    # LOGS TABLE
    execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        url TEXT,
        timestamp TIMESTAMP DEFAULT NOW()
    );
    """)

