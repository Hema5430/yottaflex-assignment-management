
import csv
from pathlib import Path

from src.database import get_connection

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GROUND_TRUTH_PATH = PROJECT_ROOT / "exports" / "ground_truth.csv"


def add_workflows():
    with get_connection() as connection:
        cursor = connection.cursor()

        # Prevent duplicate workflow records when rerunning this script.
        existing = cursor.execute(
            "SELECT COUNT(*) FROM resubmissions"
        ).fetchone()[0]

        if existing:
            raise RuntimeError(
                "Workflow records already exist. Run the data generator "
                "again before rerunning this script."
            )

        # Select ten initial submissions from different assignments.
        originals = cursor.execute("""
            SELECT s.submission_id, s.assignment_id, s.learner_id,
                   s.submitted_at, a.due_at
            FROM submissions s
            JOIN assignments a ON a.assignment_id = s.assignment_id
            WHERE s.attempt_number = 1
            ORDER BY s.submission_id
            LIMIT 10
        """).fetchall()

        for index, row in enumerate(originals, start=1):
            original_id, assignment_id, learner_id, submitted_at, due_at = row
            new_id = "SUB-{0}-{1}-02".format(assignment_id, learner_id)
            resubmission_id = "RES-2026-{0:06d}".format(index)
            artifact_id = "ART-RES-2026-{0:06d}".format(index)
            timestamp = "2026-10-22T12:00:00+00:00"

            cursor.execute("""
                INSERT INTO submissions (
                    submission_id, assignment_id, learner_id,
                    attempt_number, submitted_at, status, is_late, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_id, assignment_id, learner_id, 2,
                timestamp, "submitted", 0, timestamp
            ))

            cursor.execute("""
                INSERT INTO submission_artifacts (
                    artifact_id, submission_id, file_name, file_type,
                    file_size_bytes, checksum_sha256, storage_uri,
                    artifact_status, uploaded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                artifact_id, new_id, "resubmission_{0}.pdf".format(index),
                "application/pdf", 50000, None,
                "synthetic://artifacts/" + artifact_id,
                "available", timestamp
            ))

            cursor.execute("""
                INSERT INTO resubmissions (
                    resubmission_id, original_submission_id,
                    new_submission_id, requested_at, decision,
                    decided_by, decided_at, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                resubmission_id, original_id, new_id, timestamp,
                "approved", "INS-2026-000001", timestamp,
                "Synthetic approved resubmission example."
            ))

            cursor.execute("""
                INSERT INTO audit_events (
                    event_id, entity_type, entity_id, action,
                    old_value, new_value, actor_id, occurred_at, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "AUD-RES-2026-{0:06d}".format(index),
                "Resubmission", resubmission_id, "approved",
                "pending", "approved", "INS-2026-000001", timestamp,
                "Resubmission approved under the assignment policy."
            ))

        # Create five appeals. The first three result in grade revisions.
        graded = cursor.execute("""
            SELECT g.grade_id, g.submission_id, g.rubric_id,
                   g.raw_score, g.late_penalty, g.final_score,
                   s.learner_id
            FROM grades g
            JOIN submissions s ON s.submission_id = g.submission_id
            WHERE s.attempt_number = 1
            ORDER BY g.submission_id
            LIMIT 5
        """).fetchall()

        for index, row in enumerate(graded, start=1):
            grade_id, submission_id, rubric_id, raw, penalty, final, learner_id = row
            appeal_id = "APP-2026-{0:06d}".format(index)
            timestamp = "2026-10-23T12:00:00+00:00"
            changed = index <= 3

            revised_grade_id = None
            status = "grade_changed" if changed else "rejected"
            decision = (
                "Grade revised after appeal review."
                if changed else "Original grade upheld after review."
            )

            if changed:
                revised_grade_id = "GRD-REV-{0:06d}".format(index)
                revised_raw = min(float(raw) + 2.0, 100.0)
                revised_final = round(max(0.0, revised_raw - float(penalty)), 2)

                cursor.execute("""
                    INSERT INTO grades (
                        grade_id, submission_id, rubric_id, version,
                        raw_score, late_penalty, final_score, graded_by,
                        graded_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    revised_grade_id, submission_id, rubric_id, 2,
                    revised_raw, penalty, revised_final,
                    "INS-2026-000002", timestamp, "final"
                ))

                cursor.execute("""
                    UPDATE grades
                    SET status = 'superseded'
                    WHERE grade_id = ?
                """, (grade_id,))

                cursor.execute("""
                    INSERT INTO audit_events (
                        event_id, entity_type, entity_id, action,
                        old_value, new_value, actor_id, occurred_at, reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "AUD-GRADE-2026-{0:06d}".format(index),
                    "Grade", submission_id, "grade_revised",
                    str(final), str(revised_final),
                    "INS-2026-000002", timestamp,
                    "Appeal decision: " + decision
                ))

            cursor.execute("""
                INSERT INTO appeals (
                    appeal_id, submission_id, grade_id, learner_id,
                    reason, filed_at, status, decision, decided_by,
                    decided_at, revised_grade_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                appeal_id, submission_id, grade_id, learner_id,
                "Synthetic appeal requesting a rubric review.",
                timestamp, status, decision,
                "ADM-2026-000001", timestamp, revised_grade_id
            ))

            cursor.execute("""
                INSERT INTO audit_events (
                    event_id, entity_type, entity_id, action,
                    old_value, new_value, actor_id, occurred_at, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "AUD-APPEAL-2026-{0:06d}".format(index),
                "Appeal", appeal_id, "decided",
                "pending", status, "ADM-2026-000001", timestamp,
                decision
            ))

        connection.commit()

    # Ground truth describes intentionally tested anomaly scenarios.
    # These are labels, not corrupted production records.
    GROUND_TRUTH_PATH.parent.mkdir(parents=True, exist_ok=True)

    cases = [
        {
            "case_id": "ANOM-001",
            "issue_type": "unenrolled_learner_submission",
            "entity_type": "Submission",
            "expected_outcome": "Reject or flag submission because learner is not enrolled in the course."
        },
        {
            "case_id": "ANOM-002",
            "issue_type": "grade_exceeds_rubric_maximum",
            "entity_type": "Grade",
            "expected_outcome": "Flag grade because raw score exceeds the rubric maximum."
        },
        {
            "case_id": "ANOM-003",
            "issue_type": "duplicate_late_penalty",
            "entity_type": "Grade",
            "expected_outcome": "Flag duplicate penalty application; apply the policy once."
        },
        {
            "case_id": "ANOM-004",
            "issue_type": "appeal_without_audit_history",
            "entity_type": "Appeal",
            "expected_outcome": "Flag grade change because an audit event is missing."
        },
    ]

    with open(
        str(GROUND_TRUTH_PATH), "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "case_id", "issue_type", "entity_type", "expected_outcome"
            ],
        )
        writer.writeheader()
        writer.writerows(cases)

    print("Workflow examples created.")
    print("Approved resubmissions:", len(originals))
    print("Appeals:", len(graded))
    print("Grade revisions:", min(3, len(graded)))
    print("Ground-truth scenarios:", len(cases))
    print("Ground truth saved to:", GROUND_TRUTH_PATH)


if __name__ == "__main__":
    add_workflows()
