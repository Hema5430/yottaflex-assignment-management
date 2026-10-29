
from src.database import get_connection


def detect_anomalies():
    findings = []

    with get_connection() as connection:
        cursor = connection.cursor()

        # ANOM-001: Submission from a learner not enrolled
        rows = cursor.execute("""
            SELECT s.submission_id
            FROM submissions s
            JOIN assignments a ON a.assignment_id = s.assignment_id
            LEFT JOIN enrollments e
              ON e.course_id = a.course_id
             AND e.learner_id = s.learner_id
             AND e.status = 'enrolled'
            WHERE e.enrollment_id IS NULL
        """).fetchall()

        for row in rows:
            findings.append((
                "unenrolled_learner_submission",
                row[0],
                "Submission has no active matching course enrollment."
            ))

        # ANOM-002: Raw score exceeds rubric maximum
        rows = cursor.execute("""
            SELECT g.grade_id
            FROM grades g
            JOIN rubrics r ON r.rubric_id = g.rubric_id
            WHERE g.raw_score > r.total_points
        """).fetchall()

        for row in rows:
            findings.append((
                "grade_exceeds_rubric_maximum",
                row[0],
                "Grade raw score exceeds the rubric maximum."
            ))

        # ANOM-003: Late penalty exceeds the configured policy
        rows = cursor.execute("""
            SELECT g.grade_id
            FROM grades g
            JOIN submissions s ON s.submission_id = g.submission_id
            JOIN assignments a ON a.assignment_id = s.assignment_id
            WHERE s.is_late = 1
              AND g.late_penalty >
                  ROUND(g.raw_score * a.late_penalty_rate, 2) + 0.01
        """).fetchall()

        for row in rows:
            findings.append((
                "duplicate_late_penalty",
                row[0],
                "Late penalty exceeds the configured single-penalty amount."
            ))

        # ANOM-004: Grade-changing appeal lacks grade-revision audit event
        rows = cursor.execute("""
            SELECT a.appeal_id, a.submission_id
            FROM appeals a
            WHERE a.status = 'grade_changed'
              AND a.revised_grade_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM audit_events ev
                  WHERE ev.entity_type = 'Grade'
                    AND ev.entity_id = a.submission_id
                    AND ev.action = 'grade_revised'
              )
        """).fetchall()

        for appeal_id, submission_id in rows:
            findings.append((
                "appeal_without_audit_history",
                appeal_id,
                "Grade-changing appeal has no matching grade-revision audit event."
            ))

    print("\n=== ANOMALY DETECTION REPORT ===")

    for number, (issue_type, entity_id, description) in enumerate(
        findings, start=1
    ):
        print(
            "{}. {} | {} | {}".format(
                number, issue_type, entity_id, description
            )
        )

    print("\nTotal findings:", len(findings))
    return findings


if __name__ == "__main__":
    detect_anomalies()