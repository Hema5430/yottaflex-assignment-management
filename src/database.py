from pathlib import Path
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "yottaflex.db"
SCHEMA_PATH = PROJECT_ROOT / "src" / "schema.sql"


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(DATABASE_PATH))
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_connection() as connection:
        connection.executescript(schema)

    print("Database initialized successfully.")
    print("Database location:", DATABASE_PATH)


if __name__ == "__main__":
    initialize_database()