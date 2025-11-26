import psycopg2
from psycopg2 import sql
from utils.db import get_connection


# ============================================================
# AUTO MIGRATION SYSTEM
# ============================================================

REQUIRED_COLUMNS = {
    "pdf_used": "INTEGER DEFAULT 0",
    "scans_reset_date": "DATE"
}


def column_exists(cursor, table, column):
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name=%s AND column_name=%s
    """, (table, column))
    return cursor.fetchone() is not None


def run_migrations():
    conn = get_connection()
    cursor = conn.cursor()

    print("\n🔍 Running DB Migrations...")

    for column, datatype in REQUIRED_COLUMNS.items():
        if not column_exists(cursor, "users", column):
            print(f"➕ Adding missing column: {column}")
            cursor.execute(
                sql.SQL("ALTER TABLE users ADD COLUMN {} {};")
                .format(sql.Identifier(column), sql.SQL(datatype))
            )
            conn.commit()
        else:
            print(f"✓ Column already exists: {column}")

    cursor.close()
    conn.close()
    print("✅ Migration complete.\n")
