"""Read-only query helpers for the Streamlit Assignment Intelligence app."""

from src.database import get_connection
from src.detect_anomalies import detect_anomalies


def get_dashboard_metrics():
    tables = {
        "courses": "courses",
        "learners": "learners",
        "assignments": "assignments",
        "submissions": "submissions",
        "grades": "grades",
        "appeals": "appeals",
    }
    metrics = {}
    with get_connection() as connection:
        for key, table in tables.items():
            # Table names above are fixed constants, not user input.
            metrics[key] = connection.execute(
                "SELECT COUNT(*) FROM " + table
            ).fetchone()[0]
    return metrics


def get_anomaly_findings():
    """Use the project's existing deterministic detector; do not reimplement its rules."""
    return detect_anomalies()


def _one(connection, query, params):
    connection.row_factory = __import__("sqlite3").Row
    row = connection.execute(query, params).fetchone()
    return dict(row) if row else {"message": "No matching record was found."}


def get_anomaly_evidence(issue_type, entity_id):
    """Fetch minimal evidence for one finding using read-only SELECT queries."""
    queries = {
        "unenrolled_learner_submission": """
            SELECT s.submission_id, s.learner_id, s.assignment_id,
                   a.title AS assignment_title, a.course_id, c.course_name,
                   s.submitted_at, s.status AS submission_status,
                   e.enrollment_id, e.status AS enrollment_status
            FROM submissions s
            JOIN assignments a ON a.assignment_id = s.assignment_id
            JOIN courses c ON c.course_id = a.course_id
            LEFT JOIN enrollments e
              ON e.course_id = a.course_id
             AND e.learner_id = s.learner_id
             AND e.status = 'enrolled'
            WHERE s.submission_id = ?
        """,
        "grade_exceeds_rubric_maximum": """
            SELECT g.grade_id, g.submission_id, g.raw_score, g.final_score,
                   g.late_penalty, g.version, g.status AS grade_status,
                   r.total_points AS rubric_maximum, r.rubric_id
            FROM grades g
            JOIN rubrics r ON r.rubric_id = g.rubric_id
            WHERE g.grade_id = ?
        """,
        "duplicate_late_penalty": """
            SELECT g.grade_id, g.submission_id, g.raw_score, g.late_penalty,
                   a.late_penalty_rate,
                   ROUND(g.raw_score * a.late_penalty_rate, 2) AS expected_single_penalty,
                   s.is_late, a.assignment_id
            FROM grades g
            JOIN submissions s ON s.submission_id = g.submission_id
            JOIN assignments a ON a.assignment_id = s.assignment_id
            WHERE g.grade_id = ?
        """,
        "appeal_without_audit_history": """
            SELECT a.appeal_id, a.submission_id, a.grade_id,
                   a.revised_grade_id, a.status AS appeal_status,
                   a.reason, a.decision,
                   (SELECT COUNT(*) FROM audit_events ev
                    WHERE ev.entity_type = 'Grade'
                      AND ev.entity_id = a.submission_id
                      AND ev.action = 'grade_revised') AS matching_grade_revision_audit_events
            FROM appeals a
            WHERE a.appeal_id = ?
        """,
    }
    query = queries.get(issue_type)
    if not query:
        return {"message": "Unsupported anomaly type.", "issue_type": issue_type}
    with get_connection() as connection:
        return _one(connection, query, (entity_id,))


def get_dataset_summary():
    """Provide a small, factual summary for general AI questions."""
    with get_connection() as connection:
        summary = {}
        for table in (
            "courses", "learners", "enrollments", "assignments",
            "submissions", "grades", "feedback", "resubmissions",
            "appeals", "audit_events",
        ):
            summary[table] = connection.execute(
                "SELECT COUNT(*) FROM " + table
            ).fetchone()[0]
    return summary
