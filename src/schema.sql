
-- YottaFlex Assignment Management System
-- Database: SQLite
-- Schema version: 1

PRAGMA foreign_keys = ON;

-- 1. COURSES: Master data
CREATE TABLE IF NOT EXISTS courses (
    course_id TEXT PRIMARY KEY,
    course_name TEXT NOT NULL,
    description TEXT,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('draft', 'active', 'completed', 'archived')),
    created_at TEXT NOT NULL,
    CHECK (date(end_date) >= date(start_date))
);

-- 2. LEARNERS: Master data
CREATE TABLE IF NOT EXISTS learners (
    learner_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'suspended')),
    created_at TEXT NOT NULL
);

-- 3. COURSE ENROLLMENTS: Many-to-many relationship
CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id TEXT PRIMARY KEY,
    course_id TEXT NOT NULL,
    learner_id TEXT NOT NULL,
    enrolled_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'enrolled'
        CHECK (status IN ('enrolled', 'withdrawn', 'completed')),
    UNIQUE (course_id, learner_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id),
    FOREIGN KEY (learner_id) REFERENCES learners(learner_id)
);

-- 4. ASSIGNMENTS
CREATE TABLE IF NOT EXISTS assignments (
    assignment_id TEXT PRIMARY KEY,
    course_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    published_at TEXT,
    due_at TEXT NOT NULL,
    max_attempts INTEGER NOT NULL DEFAULT 1
        CHECK (max_attempts >= 1),
    late_penalty_rate REAL NOT NULL DEFAULT 0
        CHECK (late_penalty_rate >= 0 AND late_penalty_rate <= 1),
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'published', 'closed', 'archived')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(course_id),
    CHECK (published_at IS NULL OR
           datetime(published_at) <= datetime(due_at))
);

-- 5. RUBRICS: An assignment can have multiple rubric versions
CREATE TABLE IF NOT EXISTS rubrics (
    rubric_id TEXT PRIMARY KEY,
    assignment_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    title TEXT NOT NULL,
    total_points REAL NOT NULL CHECK (total_points > 0),
    created_at TEXT NOT NULL,
    UNIQUE (assignment_id, version),
    UNIQUE (rubric_id, assignment_id),
    FOREIGN KEY (assignment_id) REFERENCES assignments(assignment_id)
);

-- 6. RUBRIC CRITERIA
CREATE TABLE IF NOT EXISTS rubric_criteria (
    criterion_id TEXT PRIMARY KEY,
    rubric_id TEXT NOT NULL,
    criterion_name TEXT NOT NULL,
    description TEXT,
    max_points REAL NOT NULL CHECK (max_points > 0),
    weight REAL NOT NULL DEFAULT 1 CHECK (weight > 0),
    UNIQUE (rubric_id, criterion_name),
    UNIQUE (criterion_id, rubric_id),
    FOREIGN KEY (rubric_id) REFERENCES rubrics(rubric_id)
);

-- 7. SUBMISSIONS
CREATE TABLE IF NOT EXISTS submissions (
    submission_id TEXT PRIMARY KEY,
    assignment_id TEXT NOT NULL,
    learner_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL DEFAULT 1
        CHECK (attempt_number >= 1),
    submitted_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'submitted'
        CHECK (status IN (
            'submitted', 'late', 'missing', 'under_review',
            'graded', 'returned', 'resubmitted', 'rejected'
        )),
    is_late INTEGER NOT NULL DEFAULT 0 CHECK (is_late IN (0, 1)),
    created_at TEXT NOT NULL,
    UNIQUE (assignment_id, learner_id, attempt_number),
    UNIQUE (submission_id, assignment_id),
    FOREIGN KEY (assignment_id) REFERENCES assignments(assignment_id),
    FOREIGN KEY (learner_id) REFERENCES learners(learner_id)
);

-- 8. SUBMISSION ARTIFACTS: File metadata, not file contents
CREATE TABLE IF NOT EXISTS submission_artifacts (
    artifact_id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_type TEXT,
    file_size_bytes INTEGER CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0),
    checksum_sha256 TEXT,
    storage_uri TEXT,
    artifact_status TEXT NOT NULL DEFAULT 'available'
        CHECK (artifact_status IN (
            'available', 'missing', 'unreadable', 'rejected'
        )),
    uploaded_at TEXT,
    FOREIGN KEY (submission_id) REFERENCES submissions(submission_id)
);

-- 9. GRADES: Each revision is retained as a separate record
CREATE TABLE IF NOT EXISTS grades (
    grade_id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL,
    rubric_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    raw_score REAL NOT NULL CHECK (raw_score >= 0),
    late_penalty REAL NOT NULL DEFAULT 0 CHECK (late_penalty >= 0),
    final_score REAL NOT NULL CHECK (final_score >= 0),
    graded_by TEXT NOT NULL,
    graded_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'final'
        CHECK (status IN ('draft', 'final', 'superseded')),
    UNIQUE (submission_id, version),
    FOREIGN KEY (submission_id) REFERENCES submissions(submission_id),
    FOREIGN KEY (rubric_id) REFERENCES rubrics(rubric_id),
    CHECK (final_score <= raw_score)
);

-- Scores for individual rubric criteria, per grade version
CREATE TABLE IF NOT EXISTS grade_criterion_scores (
    grade_id TEXT NOT NULL,
    criterion_id TEXT NOT NULL,
    score REAL NOT NULL CHECK (score >= 0),
    PRIMARY KEY (grade_id, criterion_id),
    FOREIGN KEY (grade_id) REFERENCES grades(grade_id),
    FOREIGN KEY (criterion_id) REFERENCES rubric_criteria(criterion_id)
);

-- 10. FEEDBACK
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id TEXT PRIMARY KEY,
    grade_id TEXT NOT NULL,
    feedback_text TEXT NOT NULL,
    feedback_type TEXT NOT NULL DEFAULT 'general'
        CHECK (feedback_type IN (
            'general', 'strength', 'improvement', 'private'
        )),
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (grade_id) REFERENCES grades(grade_id)
);

-- 11. RESUBMISSIONS: Explicit link between attempts
CREATE TABLE IF NOT EXISTS resubmissions (
    resubmission_id TEXT PRIMARY KEY,
    original_submission_id TEXT NOT NULL,
    new_submission_id TEXT NOT NULL UNIQUE,
    requested_at TEXT NOT NULL,
    decision TEXT NOT NULL
        CHECK (decision IN ('pending', 'approved', 'rejected')),
    decided_by TEXT,
    decided_at TEXT,
    reason TEXT,
    FOREIGN KEY (original_submission_id) REFERENCES submissions(submission_id),
    FOREIGN KEY (new_submission_id) REFERENCES submissions(submission_id),
    CHECK (original_submission_id <> new_submission_id)
);

-- 12. APPEALS
CREATE TABLE IF NOT EXISTS appeals (
    appeal_id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL,
    grade_id TEXT NOT NULL,
    learner_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    filed_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN (
            'pending', 'under_review', 'upheld',
            'rejected', 'grade_changed', 'withdrawn'
        )),
    decision TEXT,
    decided_by TEXT,
    decided_at TEXT,
    revised_grade_id TEXT,
    FOREIGN KEY (submission_id) REFERENCES submissions(submission_id),
    FOREIGN KEY (grade_id) REFERENCES grades(grade_id),
    FOREIGN KEY (learner_id) REFERENCES learners(learner_id),
    FOREIGN KEY (revised_grade_id) REFERENCES grades(grade_id)
);

-- 13. AUDIT EVENTS: Preserve important state changes
CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    actor_id TEXT,
    occurred_at TEXT NOT NULL,
    reason TEXT
);

-- 14. VALIDATION ISSUES: Explicitly labelled anomalies
CREATE TABLE IF NOT EXISTS validation_issues (
    issue_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'error'
        CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    description TEXT NOT NULL,
    expected_outcome TEXT,
    detected_at TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0 CHECK (resolved IN (0, 1))
);

-- Helpful indexes for joins and common queries
CREATE INDEX IF NOT EXISTS idx_enrollments_learner
    ON enrollments(learner_id);

CREATE INDEX IF NOT EXISTS idx_assignments_course
    ON assignments(course_id);

CREATE INDEX IF NOT EXISTS idx_submissions_assignment_learner
    ON submissions(assignment_id, learner_id);

CREATE INDEX IF NOT EXISTS idx_submissions_submitted_at
    ON submissions(submitted_at);

CREATE INDEX IF NOT EXISTS idx_grades_submission
    ON grades(submission_id);

CREATE INDEX IF NOT EXISTS idx_appeals_status
    ON appeals(status);

CREATE INDEX IF NOT EXISTS idx_audit_entity
    ON audit_events(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_validation_issue_type
    ON validation_issues(issue_type);
