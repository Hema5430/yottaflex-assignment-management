
from src.database import get_connection


def validate_data():
    checks_passed = True

    with get_connection() as connection:
        cursor = connection.cursor()

        # Detect whether the database contains the small or full dataset.
        learner_count = cursor.execute(
            "SELECT COUNT(*) FROM learners"
        ).fetchone()[0]

        if learner_count == 100:
            expected_counts = {
                "courses": 5,
                "learners": 100,
                "assignments": 20,
                "submissions": 100,
                "submission_artifacts": 100,
                "grades": 100,
                "feedback": 100,
            }
        elif learner_count == 10000:
            expected_counts = {
                "courses": 50,
                "learners": 10000,
                "assignments": 1000,
                "submissions": 30000,
                "submission_artifacts": 30000,
                "grades": 30000,
                "feedback": 30000,
            }
        else:
            print(
                "WARNING: Unrecognized dataset size:",
                learner_count,
                "learners",
            )
            checks_passed = False
            expected_counts = {}

        print("=== RECORD COUNT CHECKS ===")

        for table, expected in expected_counts.items():
            
            if table == "submissions":
                actual = cursor.execute("""
                    SELECT COUNT(*)
                    FROM submissions
                    WHERE attempt_number = 1
                    AND submission_id != 'ANOM-SUB-001'
                    AND submission_id NOT LIKE 'SUB-WEB-%'
                """).fetchone()[0]

            elif table == "submission_artifacts":
                actual = cursor.execute("""
                    SELECT COUNT(*)
                    FROM submission_artifacts sa
                    JOIN submissions s
                      ON s.submission_id = sa.submission_id
                    WHERE s.attempt_number = 1
                      AND s.submission_id != 'ANOM-SUB-001'
                """).fetchone()[0]

            elif table == "grades":
                actual = cursor.execute("""
                    SELECT COUNT(*)
                    FROM grades
                    WHERE version = 1
                      AND grade_id != 'GRD-REV-000001'
                """).fetchone()[0]

            else:
                actual = cursor.execute(
                    "SELECT COUNT(*) FROM " + table
                ).fetchone()[0]

            passed = actual == expected

            print(
                "{}: {} (expected {}) - {}".format(
                    table,
                    actual,
                    expected,
                    "PASS" if passed else "FAIL",
                )
            )

            if not passed:
                checks_passed = False

        print("\n=== FOREIGN KEY CHECK ===")

        foreign_key_errors = cursor.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if foreign_key_errors:
            print("FAIL:", foreign_key_errors[:10])
            checks_passed = False
        else:
            print("PASS: No foreign-key violations")

        print("\n=== GRADE CHECKS ===")

        # Exclude only the deliberately injected excessive-score case.
        invalid_grades = cursor.execute("""
            SELECT g.grade_id
            FROM grades g
            JOIN rubrics r ON r.rubric_id = g.rubric_id
            WHERE g.version = 1
              AND g.grade_id != 'GRD-REV-000001'
              AND (
                  g.raw_score > r.total_points
                  OR g.final_score > g.raw_score
                  OR g.final_score < 0
              )
        """).fetchall()

        if invalid_grades:
            print(
                "FAIL: Unexpected invalid grades found:",
                len(invalid_grades),
            )
            print(
                "Grade IDs:",
                [row[0] for row in invalid_grades[:10]],
            )
            checks_passed = False
        else:
            print("PASS: No unexpected invalid original grades")

        print("\n=== ENROLLMENT CHECK ===")

        # Exclude the deliberately injected unenrolled submission.
        unenrolled = cursor.execute("""
            SELECT s.submission_id
            FROM submissions s
            JOIN assignments a
              ON a.assignment_id = s.assignment_id
            LEFT JOIN enrollments e
              ON e.course_id = a.course_id
             AND e.learner_id = s.learner_id
             AND e.status = 'enrolled'
            WHERE e.enrollment_id IS NULL
              AND s.submission_id != 'ANOM-SUB-001'
        """).fetchall()

        if unenrolled:
            print(
                "FAIL: Unexpected unenrolled submissions:",
                len(unenrolled),
            )
            print(
                "Submission IDs:",
                [row[0] for row in unenrolled[:10]],
            )
            checks_passed = False
        else:
            print("PASS: No unexpected unenrolled submissions")

    print("\n=== OVERALL RESULT ===")
    print("PASS" if checks_passed else "FAIL")

    return checks_passed


if __name__ == "__main__":
    validate_data()
