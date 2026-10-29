
import unittest

from src.database import get_connection
from src.detect_anomalies import detect_anomalies


class TestYottaFlexProject(unittest.TestCase):
    def test_required_tables_exist(self):
        expected_tables = {
            "courses", "learners", "enrollments", "assignments",
            "submissions", "submission_artifacts", "rubrics",
            "rubric_criteria", "grades", "grade_criterion_scores",
            "feedback", "resubmissions", "appeals", "audit_events",
            "validation_issues",
        }

        with get_connection() as connection:
            actual_tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }

        self.assertTrue(expected_tables.issubset(actual_tables))

    def test_database_has_no_foreign_key_violations(self):
        with get_connection() as connection:
            violations = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

        self.assertEqual(violations, [])

    def test_full_dataset_baseline_exists(self):
        expected = {
            "courses": 50,
            "learners": 10000,
            "assignments": 1000,
            "feedback": 30000,
        }

        with get_connection() as connection:
            for table, count in expected.items():
                actual = connection.execute(
                    "SELECT COUNT(*) FROM " + table
                ).fetchone()[0]
                self.assertEqual(actual, count, table)

    def test_four_anomaly_types_are_detected(self):
        findings = detect_anomalies()
        issue_types = {finding[0] for finding in findings}

        expected = {
            "unenrolled_learner_submission",
            "grade_exceeds_rubric_maximum",
            "duplicate_late_penalty",
            "appeal_without_audit_history",
        }

        self.assertTrue(expected.issubset(issue_types))

    def test_ten_approved_resubmissions_exist(self):
        with get_connection() as connection:
            count = connection.execute(
                """
                SELECT COUNT(*) FROM resubmissions
                WHERE decision = 'approved'
                """
            ).fetchone()[0]

        self.assertEqual(count, 10)

    def test_regular_appeals_and_audit_history_are_preserved(self):
        with get_connection() as connection:
            appeals = connection.execute(
                """
                SELECT COUNT(*) FROM appeals
                WHERE appeal_id != 'ANOM-APP-004'
                """
            ).fetchone()[0]

            audit_events = connection.execute(
                """
                SELECT COUNT(*) FROM audit_events
                WHERE entity_type = 'Grade'
                  AND action = 'grade_revised'
                """
            ).fetchone()[0]

        self.assertEqual(appeals, 5)
        self.assertEqual(audit_events, 3)


if __name__ == "__main__":
    unittest.main()
