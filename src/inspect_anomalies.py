
from src.database import get_connection

query = """
SELECT
    g.grade_id,
    g.submission_id,
    g.version,
    g.raw_score,
    g.late_penalty,
    g.final_score,
    s.is_late,
    a.late_penalty_rate,
    ROUND(g.raw_score * a.late_penalty_rate, 2)
        AS expected_penalty
FROM grades g
JOIN submissions s
    ON s.submission_id = g.submission_id
JOIN assignments a
    ON a.assignment_id = s.assignment_id
WHERE g.grade_id = ?
"""

grade_ids = [
    "GRD-SUB-ASN-2026-000002-LRN-2026-000012-01",
    "ANOM-GRD-004",
]

with get_connection() as connection:
    for grade_id in grade_ids:
        row = connection.execute(query, (grade_id,)).fetchone()

        print("\nGrade:", grade_id)

        if row is None:
            print("Record not found.")
        else:
            labels = [
                "grade_id", "submission_id", "version",
                "raw_score", "late_penalty", "final_score",
                "is_late", "penalty_rate", "expected_penalty",
            ]

            for label, value in zip(labels, row):
                print("{}: {}".format(label, value))