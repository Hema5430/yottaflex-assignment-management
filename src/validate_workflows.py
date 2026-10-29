

from src.database import get_connection


def run_check(name, query, expected):
    with get_connection() as connection:
        result = connection.execute(query).fetchone()[0]

    passed = result == expected
    print(
        "{}: {} (expected {}) - {}".format(
            name, result, expected, "PASS" if passed else "FAIL"
        )
    )
    return passed


def validate_workflows():
    checks = [
        (
            "Approved resubmissions",
            "SELECT COUNT(*) FROM resubmissions WHERE decision = 'approved'",
            10,
        ),
        (
            "Appeals recorded (excluding injected anomaly)",
            """
            SELECT COUNT(*)
            FROM appeals
            WHERE appeal_id != 'ANOM-APP-004'
            """,
            5,
        ),
        (
            "Grade-change appeals (excluding injected anomaly)",
            """
            SELECT COUNT(*)
            FROM appeals
            WHERE status = 'grade_changed'
              AND appeal_id != 'ANOM-APP-004'
            """,
            3,
        ),
        (
            "Revised grades linked to appeals",
            """
            SELECT COUNT(*)
            FROM appeals a
            JOIN grades g ON g.grade_id = a.revised_grade_id
            WHERE a.status = 'grade_changed'
              AND a.appeal_id != 'ANOM-APP-004'
              AND g.version = 2
            """,
            3,
        ),
        (
            "Appeal audit events",
            """
            SELECT COUNT(*)
            FROM audit_events
            WHERE entity_type = 'Appeal'
              AND action = 'decided'
            """,
            5,
        ),
        (
            "Grade revision audit events",
            """
            SELECT COUNT(*)
            FROM audit_events
            WHERE entity_type = 'Grade'
              AND action = 'grade_revised'
            """,
            3,
        ),
        (
            "Ground-truth scenarios",
            "SELECT COUNT(*) FROM validation_issues",
            0,
        ),
    ]

    print("=== WORKFLOW VALIDATION ===")
    passed_count = 0

    for name, query, expected in checks:
        if run_check(name, query, expected):
            passed_count += 1

    print("\nChecks passed: {}/{}".format(passed_count, len(checks)))
    print(
        "OVERALL:",
        "PASS" if passed_count == len(checks) else "FAIL",
    )


if __name__ == "__main__":
    validate_workflows()