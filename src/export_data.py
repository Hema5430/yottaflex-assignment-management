
import csv
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = ROOT / "data" / "yottaflex.db"
EXPORT_DIR = ROOT / "exports"

TABLES = [
    "learners",
    "courses",
    "enrollments",
    "assignments",
    "submissions",
    "submission_artifacts",
    "rubrics",
    "rubric_criteria",
    "grades",
    "grade_criterion_scores",
    "feedback",
    "resubmissions",
    "appeals",
    "audit_events",
    "validation_issues",
]


def export_data():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        for table in TABLES:
            rows = connection.execute(
                f'SELECT * FROM "{table}"'
            ).fetchall()

            records = [dict(row) for row in rows]

            # Export CSV
            csv_path = EXPORT_DIR / f"{table}.csv"

            if records:
                with open(
                    csv_path, "w", newline="", encoding="utf-8"
                ) as file:
                    writer = csv.DictWriter(
                        file, fieldnames=records[0].keys()
                    )
                    writer.writeheader()
                    writer.writerows(records)
            else:
                columns = connection.execute(
                    f'PRAGMA table_info("{table}")'
                ).fetchall()

                with open(
                    csv_path, "w", newline="", encoding="utf-8"
                ) as file:
                    writer = csv.writer(file)
                    writer.writerow([column["name"] for column in columns])

            # Export JSON
            json_path = EXPORT_DIR / f"{table}.json"

            with open(json_path, "w", encoding="utf-8") as file:
                json.dump(records, file, indent=2, default=str)

        # Export a SQL database snapshot
        sql_path = EXPORT_DIR / "yottaflex_export.sql"

        with open(sql_path, "w", encoding="utf-8") as file:
            for line in connection.iterdump():
                file.write(line + "\n")

        print("Exports completed successfully.")
        print(f"Export directory: {EXPORT_DIR}")
        print(f"Tables exported: {len(TABLES)}")
        print("Formats: CSV, JSON, SQL")

    finally:
        connection.close()


if __name__ == "__main__":
    export_data()
