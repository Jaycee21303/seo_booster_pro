import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    """
    Creates the users table if missing,
    and adds required columns (safe auto-migration).
    """
    conn = get_connection()
    cursor = conn.cursor()

    # --- BASE TABLE CREATION ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            api_key TEXT
        );
    """)

    # --- SAFE COLUMN ADDITIONS ---
    required_columns = {
        "scans_used": "INTEGER DEFAULT 0",
        "is_pro": "BOOLEAN DEFAULT FALSE"
    }

    for column, definition in required_columns.items():
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name=%s;
        """, (column,))

        exists = cursor.fetchone()
        if not exists:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {definition};")
            print(f"Added missing column: {column}")

    conn.commit()
    cursor.close()
    conn.close()


# --- QUERY HELPERS ---

def fetch_one(query, params=None):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(query, params or ())
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

def fetch_all(query, params=None):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(query, params or ())
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def execute(query, params=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params or ())
    conn.commit()
    cursor.close()
    conn.close()


