import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# ============================================================
#  DATABASE INITIALIZATION / AUTO-MIGRATION
# ============================================================

def init_db():
    """
    Builds tables if missing, and auto-adds columns safely.
    NEVER deletes/modifies existing user data.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # --------------------------------------------------------
    # USERS TABLE
    # --------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            api_key TEXT
        );
    """)

    required_user_columns = {
        "scans_used": "INTEGER DEFAULT 0",
        "is_pro": "BOOLEAN DEFAULT FALSE",
        "is_admin": "BOOLEAN DEFAULT FALSE",
        "stripe_customer_id": "TEXT",
        "stripe_subscription_id": "TEXT",
        "subscription_status": "TEXT",
        "current_period_end": "TIMESTAMP"
    }

    # Add missing columns safely
    for column, definition in required_user_columns.items():
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='users' AND column_name=%s;
        """, (column,))
        exists = cursor.fetchone()

        if not exists:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {definition};")
            print(f"[DB] Added missing column to users: {column}")

    # --------------------------------------------------------
    # SUBSCRIPTIONS TABLE
    # (Each user may have 0–1 active subscription)
    # --------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            status TEXT,
            current_period_end TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()


# ============================================================
#  QUERY HELPERS
# ============================================================

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


# ============================================================
#  RUN MIGRATIONS ON SERVICE STARTUP
# ============================================================

init_db()
