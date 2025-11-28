import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DB_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# -------------------------------------------------------------
# CREATE NEW USER
# -------------------------------------------------------------
def create_user(email, password):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute(
        """
        INSERT INTO users (email, password, is_pro, subscription_status)
        VALUES (%s, %s, FALSE, 'free')
        """,
        (email, password)
    )

    conn.commit()
    cur.close()
    conn.close()


# -------------------------------------------------------------
# CREATE ADMIN USER (AUTO)
# -------------------------------------------------------------
def create_admin():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT * FROM users WHERE email = 'admin@admin.com'")
    exists = cur.fetchone()

    if not exists:
        cur.execute(
            """
            INSERT INTO users (email, password, is_pro, subscription_status, is_admin, scans_used)
            VALUES ('admin@admin.com', 'admin123', TRUE, 'active', TRUE, 0)
            """
        )
        conn.commit()

    cur.close()
    conn.close()


# -------------------------------------------------------------
# LIST USERS (admin panel)
# -------------------------------------------------------------
def list_users():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute(
        """
        SELECT 
            id,
            email,
            is_pro,
            is_admin,
            scans_used
        FROM users
        ORDER BY id ASC
        """
    )

    users = cur.fetchall()

    cur.close()
    conn.close()
    return users


# -------------------------------------------------------------
# DELETE USER BY ID
# -------------------------------------------------------------
def delete_user_by_id(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()


# -------------------------------------------------------------
# RESET SCANS
# -------------------------------------------------------------
def reset_scans(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET scans_used = 0 WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()


# -------------------------------------------------------------
# MAKE ADMIN
# -------------------------------------------------------------
def make_admin(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_admin = TRUE WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()


# -------------------------------------------------------------
# RESET PASSWORD
# -------------------------------------------------------------
def reset_password(email, new_password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password = %s WHERE email = %s",
        (new_password, email)
    )
    conn.commit()
    cur.close()
    conn.close()


# -------------------------------------------------------------
# UPDATE USER (EMAIL / PRO / ADMIN / PASSWORD)
# -------------------------------------------------------------
def update_user(user_id, email, is_pro, is_admin, password=None):
    conn = get_connection()
    cur = conn.cursor()

    if password:
        cur.execute(
            """
            UPDATE users
            SET email=%s, is_pro=%s, is_admin=%s, password=%s
            WHERE id=%s
            """,
            (email, is_pro, is_admin, password, user_id)
        )
    else:
        cur.execute(
            """
            UPDATE users
            SET email=%s, is_pro=%s, is_admin=%s
            WHERE id=%s
            """,
            (email, is_pro, is_admin, user_id)
        )

    conn.commit()
    cur.close()
    conn.close()


# -------------------------------------------------------------
# GET USER BY EMAIL
# -------------------------------------------------------------
def get_user_by_email(email):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute(
        """
        SELECT *
        FROM users
        WHERE email = %s
        """,
        (email,)
    )

    user = cur.fetchone()
    cur.close()
    conn.close()
    return user


# -------------------------------------------------------------
# GET USER BY SUBSCRIPTION ID
# -------------------------------------------------------------
def get_user_by_subscription(subscription_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute(
        """
        SELECT *
        FROM users
        WHERE stripe_subscription_id = %s
        """,
        (subscription_id,)
    )

    user = cur.fetchone()
    cur.close()
    conn.close()
    return user


# -------------------------------------------------------------
# UPDATE SUBSCRIPTION
# -------------------------------------------------------------
def update_subscription_by_email(email, stripe_customer_id, stripe_subscription_id,
                                 status, is_pro, period_end):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE users
        SET 
            stripe_customer_id = %s,
            stripe_subscription_id = %s,
            subscription_status = %s,
            is_pro = %s,
            subscription_period_end = %s
        WHERE email = %s
        """,
        (
            stripe_customer_id,
            stripe_subscription_id,
            status,
            is_pro,
            period_end,
            email
        )
    )

    conn.commit()
    cur.close()
    conn.close()
