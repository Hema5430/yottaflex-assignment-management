

from pathlib import Path

from src.database import get_connection

ROOT = Path(__file__).resolve().parent.parent


def inject_anomalies():
    with get_connection() as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        # Case 1: A learner submits without enrollment in the course.
        submission_id = "ANOM-SUB-001"

        exists = connection.execute(
            "SELECT 1 FROM submissions WHERE submission_id = ?",
            (submission_id,),
        ).fetchone()

        if not exists:
            candidate = connection.execute(
                """
                SELECT a.assignment_id, a.course_id, l.learner_id
                FROM assignments a
                CROSS JOIN learners l
                WHERE NOT EXISTS (
                    SELECT 1 FROM enrollments e
                    WHERE e.course_id = a.course_id
                      AND e.learner_id = l.learner_id
                      AND e.status = 'enrolled'
                )
                AND NOT EXISTS (
                    SELECT 1 FROM submissions s
                    WHERE s.assignment_id = a.assignment_id
                      AND s.learner_id = l.learner_id
                      AND s.attempt_number = 1
                )
                ORDER BY a.assignment_id, l.learner_id
                LIMIT 1
                """
            ).fetchone()

            if candidate:
                connection.execute(
                    """
                    INSERT INTO submissions (
                        submission_id, assignment_id, learner_id,
                        attempt_number, submitted_at, status,
                        is_late, created_at
                    )
                    VALUES (?, ?, ?, 1, ?, 'submitted', 0, ?)
                    """,
                    (
                        submission_id,
                        candidate[0],
                        candidate[2],
                        "2026-10-20T12:00:00",
                        "2026-10-20T12:00:00",
                    ),
                )

        # Case 2: Final score exceeds its rubric's maximum.
        existing = connection.execute(
            """
            SELECT g.grade_id
            FROM grades g
            JOIN rubrics r ON r.rubric_id = g.rubric_id
            WHERE g.final_score > r.total_points
            LIMIT 1
            """
        ).fetchone()

        if not existing:
            candidate = connection.execute(
                """
                SELECT g.grade_id, r.total_points
                FROM grades g
                JOIN rubrics r ON r.rubric_id = g.rubric_id
                WHERE g.status = 'final'
                  AND g.final_score <= r.total_points
                  AND g.grade_id <> 'GRD-REV-000001'
                ORDER BY g.grade_id
                LIMIT 1
                """
            ).fetchone()

            if candidate:
                grade_id, maximum = candidate
                bad_score = round(float(maximum) + 10.0, 2)

                connection.execute(
                    """
                    UPDATE grades
                    SET raw_score = ?, final_score = ?
                    WHERE grade_id = ?
                    """,
                    (bad_score, bad_score, grade_id),
                )

        # Case 3: Late penalty is deliberately doubled.
        existing = connection.execute(
            """
            SELECT g.grade_id
            FROM grades g
            JOIN submissions s ON s.submission_id = g.submission_id
            JOIN assignments a ON a.assignment_id = s.assignment_id
            WHERE s.is_late = 1
              AND g.late_penalty >
                  ROUND(g.raw_score * a.late_penalty_rate, 2) + 0.01
            LIMIT 1
            """
        ).fetchone()

        if not existing:
            candidate = connection.execute(
                """
                SELECT g.grade_id, g.raw_score, a.late_penalty_rate
                FROM grades g
                JOIN submissions s ON s.submission_id = g.submission_id
                JOIN assignments a ON a.assignment_id = s.assignment_id
                WHERE s.is_late = 1
                  AND a.late_penalty_rate > 0
                  AND g.status = 'final'
                ORDER BY g.grade_id
                LIMIT 1
                """
            ).fetchone()

            if candidate:
                grade_id, raw_score, rate = candidate
                penalty = round(float(raw_score) * float(rate), 2)
                bad_penalty = round(penalty * 2, 2)
                final_score = round(
                    max(0.0, float(raw_score) - bad_penalty), 2
                )

                connection.execute(
                    """
                    UPDATE grades
                    SET late_penalty = ?, final_score = ?
                    WHERE grade_id = ?
                    """,
                    (bad_penalty, final_score, grade_id),
                )

        # Case 4: Appeal revises a grade without a grade-revision audit.
        appeal_id = "ANOM-APP-004"
        revised_grade_id = "ANOM-GRD-004"

        appeal_exists = connection.execute(
            "SELECT 1 FROM appeals WHERE appeal_id = ?",
            (appeal_id,),
        ).fetchone()

        revised_exists = connection.execute(
            "SELECT 1 FROM grades WHERE grade_id = ?",
            (revised_grade_id,),
        ).fetchone()

        if not appeal_exists and not revised_exists:
            candidate = connection.execute(
                """
                SELECT
                    g.grade_id, g.submission_id, g.rubric_id,
                    g.raw_score, g.graded_by, g.version,
                    r.total_points, s.learner_id,
                    a.late_penalty_rate, s.is_late
                FROM grades g
                JOIN submissions s ON s.submission_id = g.submission_id
                JOIN assignments a ON a.assignment_id = s.assignment_id
                JOIN rubrics r ON r.rubric_id = g.rubric_id
                WHERE g.status = 'final'
                  AND NOT EXISTS (
                      SELECT 1 FROM appeals ap
                      WHERE ap.submission_id = g.submission_id
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM grades newer
                      WHERE newer.submission_id = g.submission_id
                        AND newer.version > g.version
                  )
                ORDER BY g.grade_id
                LIMIT 1
                """
            ).fetchone()

            if candidate:
                (
                    old_grade_id, sub_id, rubric_id, raw_score,
                    graded_by, version, maximum, learner_id,
                    penalty_rate, is_late,
                ) = candidate

                revised_raw = round(
                    min(float(raw_score) + 1.0, float(maximum)), 2
                )
                if revised_raw == float(raw_score):
                    revised_raw = round(
                        max(0.0, float(raw_score) - 1.0), 2
                    )

                penalty = (
                    round(revised_raw * float(penalty_rate), 2)
                    if is_late else 0.0
                )
                final_score = round(max(0.0, revised_raw - penalty), 2)

                connection.execute(
                    """
                    UPDATE grades SET status = 'superseded'
                    WHERE grade_id = ?
                    """,
                    (old_grade_id,),
                )

                connection.execute(
                    """
                    INSERT INTO grades (
                        grade_id, submission_id, rubric_id, version,
                        raw_score, late_penalty, final_score,
                        graded_by, graded_at, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'final')
                    """,
                    (
                        revised_grade_id, sub_id, rubric_id,
                        int(version) + 1, revised_raw, penalty,
                        final_score, graded_by,
                        "2026-10-25T10:00:00",
                    ),
                )

                connection.execute(
                    """
                    INSERT INTO appeals (
                        appeal_id, submission_id, grade_id, learner_id,
                        reason, filed_at, status, decision,
                        decided_by, decided_at, revised_grade_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 'grade_changed', ?, ?, ?, ?)
                    """,
                    (
                        appeal_id, sub_id, old_grade_id, learner_id,
                        "Synthetic appeal testing missing grade audit history.",
                        "2026-10-24T09:00:00",
                        "Grade revised without audit event",
                        graded_by,
                        "2026-10-25T10:00:00",
                        revised_grade_id,
                    ),
                )

                # Intentionally omit the grade-revision audit event.

        connection.commit()

    print("Anomaly injection finished.")


if __name__ == "__main__":
    inject_anomalies()
