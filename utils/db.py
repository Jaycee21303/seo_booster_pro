import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DB_URL")


def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# -----------------------------
# CREATE NEW USER
# -----------------------------
def create_user(email, password):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        INSERT INTO users (email, password, is_pro, subscription_status)
        VALUES (%s, %s, FALSE, 'free')
    """, (email, password))

    conn.commit()
    cur.close()
    conn.close()


# -----------------------------
# GET USER BY EMAIL
# -----------------------------
def get_user_by_email(email):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cur.fetchone()

    cur.close()
    conn.close()
    return user


# -----------------------------
# GET USER BY SUBSCRIPTION ID
# -----------------------------
def get_user_by_subscription(subscription_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT * FROM users
        WHERE stripe_subscription_id = %s
    """, (subscription_id,))

    user = cur.fetchone()
    cur.close()
    conn.close()
    return user


# -----------------------------
# UPDATE SUBSCRIPTION BY EMAIL
# -----------------------------
def update_subscription_by_email(email, stripe_customer_id, stripe_subscription_id,
                                 status, is_pro, period_end):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET 
            stripe_customer_id = %s,
            stripe_subscription_id = %s,
            subscription_status = %s_
