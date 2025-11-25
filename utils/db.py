import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Create table if missing
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            api_key TEXT
        );
    """)

    # Missing columns that MUST be added
    required_user_columns = {
        "is_admin": "BOOLEAN DEFAULT FALSE",
        "is_pro": "BOOLEAN DEFAULT FALSE",
        "scans_used": "INTEGER DEFAULT 0",
        "stripe_customer_id": "TEXT",
        "stripe_subscription_id": "TEXT",
        "subscription_status": "TEXT",
        "current_period_end": "TIMESTAMP"
    }

    for column, definition in required_user_columns.items():
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name=%s;
        """, (column,))
        exists = cursor.fetchone()

        if not exists:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {definition};")
            print(f"[DB] Added missing user column: {column}")

    conn.commit()
    cursor.close()
    conn.close()


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


# Auto-run migrations
init_db()
