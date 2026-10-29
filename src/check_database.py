
from src.database import get_connection

with get_connection() as connection:
    cursor = connection.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)

    tables = cursor.fetchall()

    print(f"\nTotal tables created: {len(tables)}")
    for table in tables:
        print("-", table[0])

    cursor.execute("PRAGMA foreign_key_check")
    errors = cursor.fetchall()

    if errors:
        print("\nForeign-key problems:", errors)
    else:
        print("\nForeign-key check passed.")