import psycopg2
from psycopg2.extras import RealDictCursor
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


# --------------------------
# USER LOOKUP HELPERS
# --------------------------

def get_user_by_email(email):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user


# --------------------------
# USER UPDATE HELPERS
# --------------------------

def update_subscription(user_id, customer_id, subscription_id, status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET
            stripe_customer_id = %s,
            stripe_subscription_id = %s,
            subscription_status = %s,
            is_pro = %s
        WHERE id = %s
    """, (
        customer_id,
        subscription_id,
        status,
        status == "active",
        user_id,
    ))

    conn.commit()
    conn.close()


def create_user(email, password_hash):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users (email, password, is_pro, subscription_status)
        VALUES (%s, %s, FALSE, 'none')
        RETURNING id
    """, (email, password_hash))

    new_id = cur.fetchone()["id"]

    conn.commit()
    conn.close()

    return new_id
