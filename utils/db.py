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


def get_user_by_subscription(subscription_id):
    """Used when Stripe sends subscription.updated events."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM users
        WHERE stripe_subscription_id = %s
    """, (subscription_id,))

    user = cur.fetchone()
    conn.close()
    return user


# --------------------------
# UPDATE HELPERS
# --------------------------

def update_subscription_by_email(
    email,
    stripe_customer_id,
    stripe_subscription_id,
    status,
    is_pro,
    period_end
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET
            stripe_customer_id = %s,
            stripe_subscription_id = %s,
            subscription_status = %s,
            is_pro = %s,
            period_end = %s
        WHERE email = %s
    """, (
        stripe_customer_id,
        stripe_subscription_id,
        status,
        is_pro,
        period_end,
        email
    ))

    conn.commit()
    conn.close()


def update_subscription_by_id(
    user_id,
    stripe_customer_id,
    stripe_subscription_id,
    status,
    is_pro,
    period_end
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET
            stripe_customer_id = %s,
            stripe_subscription_id = %s,
            subscription_status = %s,
            is_pro = %s,
            period_end = %s
        WHERE id = %s
    """, (
        stripe_customer_id,
        stripe_subscription_id,
        status,
        is_pro,
        period_end,
        user_id
    ))

    conn.commit()
    conn.close()


# --------------------------
# CREATE USER
# --------------------------

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
