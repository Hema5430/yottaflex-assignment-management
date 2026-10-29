
import argparse
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.database import DATABASE_PATH, get_connection

SEED = 20261022


def timestamp(value):
    """Return an ISO 8601 UTC timestamp."""
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def generate_data(small=False):
    rng = random.Random(SEED)

    # Small mode tests the same generator at a smaller scale.
    if small:
        course_count = 5
        learner_count = 100
        assignment_count = 20
        submissions_per_assignment = 5
    else:
        course_count = 50
        learner_count = 10000
        assignment_count = 1000
        submissions_per_assignment = 30

    now = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    # Ensure assignments are evenly distributed across courses.
    if assignment_count % course_count != 0:
        raise ValueError("Assignments must divide evenly across courses.")

    if learner_count % course_count != 0:
        raise ValueError("Learners must divide evenly across courses.")

    learners_per_course = learner_count // course_count

    # Keep every generated submission associated with an enrolled learner.
    if submissions_per_assignment > learners_per_course:
        raise ValueError("Not enough enrolled learners per course.")

    with get_connection() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        cursor = connection.cursor()

        # Clear existing generated data in dependency-safe order.
        # Use a dedicated challenge database; this deletes prior records.
        tables_to_clear = [
            "validation_issues",
            "appeals",
            "resubmissions",
            "feedback",
            "grade_criterion_scores",
            "grades",
            "submission_artifacts",
            "submissions",
            "rubric_criteria",
            "rubrics",
            "assignments",
            "enrollments",
            "learners",
            "courses",
            "audit_events",
        ]

        for table in tables_to_clear:
            cursor.execute("DELETE FROM " + table)

        print("Generating courses...")
        for i in range(1, course_count + 1):
            course_id = "CRS-2026-{0:06d}".format(i)
            start_date = "2026-01-01"
            end_date = "2026-12-31"

            cursor.execute(
                """
                INSERT INTO courses
                (course_id, course_name, description, start_date,
                 end_date, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    course_id,
                    "Synthetic Course {0:03d}".format(i),
                    "Generated course for workflow testing.",
                    start_date,
                    end_date,
                    "active",
                    timestamp(start),
                ),
            )

        print("Generating learners and enrollments...")
        learners_by_course = {
            i: [] for i in range(1, course_count + 1)
        }

        for i in range(1, learner_count + 1):
            learner_id = "LRN-2026-{0:06d}".format(i)
            course_number = ((i - 1) % course_count) + 1
            course_id = "CRS-2026-{0:06d}".format(course_number)
            learner_name = "Synthetic Learner {0:06d}".format(i)
            email = "learner{0:06d}@example.invalid".format(i)

            learners_by_course[course_number].append(learner_id)

            cursor.execute(
                """
                INSERT INTO learners
                (learner_id, full_name, email, status, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    learner_id,
                    learner_name,
                    email,
                    "active",
                    timestamp(start),
                ),
            )

            enrollment_id = "ENR-2026-{0:06d}".format(i)
            cursor.execute(
                """
                INSERT INTO enrollments
                (enrollment_id, course_id, learner_id, enrolled_at, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    enrollment_id,
                    course_id,
                    learner_id,
                    timestamp(start + timedelta(days=course_number)),
                    "enrolled",
                ),
            )

        print("Generating assignments and rubrics...")
        assignments_by_course = {
            i: [] for i in range(1, course_count + 1)
        }

        assignments_per_course = assignment_count // course_count

        for i in range(1, assignment_count + 1):
            assignment_id = "ASN-2026-{0:06d}".format(i)
            course_number = ((i - 1) % course_count) + 1
            course_id = "CRS-2026-{0:06d}".format(course_number)

            created = start + timedelta(days=i % 60)
            published = created + timedelta(days=1)
            due = published + timedelta(days=14)

            assignments_by_course[course_number].append(assignment_id)

            cursor.execute(
                """
                INSERT INTO assignments
                (assignment_id, course_id, title, description,
                 published_at, due_at, max_attempts, late_penalty_rate,
                 status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assignment_id,
                    course_id,
                    "Assignment {0:06d}".format(i),
                    "Synthetic assignment for workflow testing.",
                    timestamp(published),
                    timestamp(due),
                    2,
                    0.10,
                    "published",
                    timestamp(created),
                ),
            )

            rubric_id = "RUB-{0}-01".format(assignment_id)
            cursor.execute(
                """
                INSERT INTO rubrics
                (rubric_id, assignment_id, version, title,
                 total_points, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    rubric_id,
                    assignment_id,
                    1,
                    "Standard 100-point rubric",
                    100.0,
                    timestamp(created),
                ),
            )

            criteria = [
                ("Content", 40.0),
                ("Analysis", 35.0),
                ("Presentation", 25.0),
            ]

            for j, (name, maximum) in enumerate(criteria, start=1):
                criterion_id = "{0}-CRIT-{1:02d}".format(rubric_id, j)
                cursor.execute(
                    """
                    INSERT INTO rubric_criteria
                    (criterion_id, rubric_id, criterion_name,
                     description, max_points, weight)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        criterion_id,
                        rubric_id,
                        name,
                        "Synthetic scoring criterion.",
                        maximum,
                        1.0,
                    ),
                )

        print("Generating submissions, artifacts, grades and feedback...")
        submission_number = 0
        artifact_number = 0
        grade_number = 0
        feedback_number = 0

        for assignment_index in range(1, assignment_count + 1):
            assignment_id = "ASN-2026-{0:06d}".format(assignment_index)
            course_number = ((assignment_index - 1) % course_count) + 1
            learner_pool = learners_by_course[course_number]

            rubric_id = "RUB-{0}-01".format(assignment_id)
            due_at = start + timedelta(
                days=(assignment_index % 60) + 15
            )

            # Use unique learners for each assignment's initial submissions.
            selected_learners = rng.sample(
                learner_pool, submissions_per_assignment
            )

            for learner_id in selected_learners:
                submission_number += 1
                submission_id = "SUB-{0}-{1}-01".format(
                    assignment_id, learner_id
                )

                is_late = rng.random() < 0.15
                submitted_at = due_at + timedelta(
                    hours=rng.randint(1, 72)
                ) if is_late else due_at - timedelta(
                    hours=rng.randint(1, 240)
                )

                submitted_text = timestamp(submitted_at)
                status = "late" if is_late else "submitted"

                cursor.execute(
                    """
                    INSERT INTO submissions
                    (submission_id, assignment_id, learner_id,
                     attempt_number, submitted_at, status, is_late,
                     created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        submission_id,
                        assignment_id,
                        learner_id,
                        1,
                        submitted_text,
                        status,
                        int(is_late),
                        submitted_text,
                    ),
                )

                artifact_number += 1
                artifact_id = "ART-2026-{0:07d}".format(artifact_number)
                artifact_status = (
                    "missing" if rng.random() < 0.03 else "available"
                )

                cursor.execute(
                    """
                    INSERT INTO submission_artifacts
                    (artifact_id, submission_id, file_name, file_type,
                     file_size_bytes, checksum_sha256, storage_uri,
                     artifact_status, uploaded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        artifact_id,
                        submission_id,
                        "submission_{0}.pdf".format(submission_number),
                        "application/pdf",
                        None if artifact_status == "missing"
                        else rng.randint(10000, 2000000),
                        None,
                        "synthetic://artifacts/" + artifact_id,
                        artifact_status,
                        submitted_text,
                    ),
                )

                scores = [
                    rng.randint(20, 40),
                    rng.randint(15, 35),
                    rng.randint(10, 25),
                ]
                raw_score = float(sum(scores))
                penalty = round(raw_score * 0.10, 2) if is_late else 0.0
                final_score = round(max(0.0, raw_score - penalty), 2)

                grade_number += 1
                grade_id = "GRD-{0}".format(submission_id)

                cursor.execute(
                    """
                    INSERT INTO grades
                    (grade_id, submission_id, rubric_id, version,
                     raw_score, late_penalty, final_score, graded_by,
                     graded_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        grade_id,
                        submission_id,
                        rubric_id,
                        1,
                        raw_score,
                        penalty,
                        final_score,
                        "INS-2026-000001",
                        timestamp(now),
                        "final",
                    ),
                )

                criterion_rows = cursor.execute(
                    """
                    SELECT criterion_id
                    FROM rubric_criteria
                    WHERE rubric_id = ?
                    ORDER BY criterion_name
                    """,
                    (rubric_id,),
                ).fetchall()

                # Keep score-to-criterion mapping explicit.
                # Order is Content, Analysis, Presentation.
                criterion_ids = {
                    row[0].split("-CRIT-")[-1]: row[0]
                    for row in criterion_rows
                }

                for criterion_number, score in enumerate(scores, start=1):
                    criterion_id = (
                        "{0}-CRIT-{1:02d}".format(
                            rubric_id, criterion_number
                        )
                    )
                    cursor.execute(
                        """
                        INSERT INTO grade_criterion_scores
                        (grade_id, criterion_id, score)
                        VALUES (?, ?, ?)
                        """,
                        (grade_id, criterion_id, float(score)),
                    )

                feedback_number += 1
                cursor.execute(
                    """
                    INSERT INTO feedback
                    (feedback_id, grade_id, feedback_text,
                     feedback_type, created_by, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "FDB-2026-{0:07d}".format(feedback_number),
                        grade_id,
                        "Synthetic feedback: review the rubric criteria "
                        "and use the feedback to improve your next attempt.",
                        "general",
                        "INS-2026-000001",
                        timestamp(now),
                    ),
                )

        # Record generation settings for reproducibility.
        connection.commit()

        print("\nGeneration completed.")
        print("Seed:", SEED)
        print("Courses:", course_count)
        print("Learners:", learner_count)
        print("Assignments:", assignment_count)
        print("Initial submissions:", submission_number)
        print("Artifacts:", artifact_number)
        print("Grades:", grade_number)
        print("Feedback records:", feedback_number)
        print("Database:", DATABASE_PATH)


def main():
    parser = argparse.ArgumentParser(
        description="Generate reproducible YottaFlex synthetic data."
    )
    parser.add_argument(
        "--small",
        action="store_true",
        help="Generate a small dataset for initial testing.",
    )
    args = parser.parse_args()
    generate_data(small=args.small)


if __name__ == "__main__":
    main()