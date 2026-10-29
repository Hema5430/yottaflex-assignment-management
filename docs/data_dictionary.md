# YottaFlex Assignment Management System — Data Dictionary

**Version:** 1.0  
**Database:** SQLite  
**Purpose:** Define the entities, fields, relationships, and validation rules for the synthetic assignment-management dataset.

## 1. General conventions

- IDs are immutable text identifiers and must be unique within their entity.
- Dates and timestamps use ISO 8601 format. Timestamps should include a timezone offset, preferably UTC (`+00:00`).
- Boolean fields use `0` for false and `1` for true.
- Scores and penalties are numeric values.
- Synthetic learner names and email addresses must not represent real personal records.
- Derived values must be calculated from source records rather than generated independently.
- Important state changes must be retained in audit history.

## 2. Core entities

### Course

| Field | Type | Required | Validation |
|---|---|---|---|
| course_id | TEXT | Yes | Primary key; unique and immutable |
| course_name | TEXT | Yes | Must not be empty |
| description | TEXT | No | Optional text |
| start_date | TEXT | Yes | Valid ISO date |
| end_date | TEXT | Yes | Must be on or after start_date |
| status | TEXT | Yes | draft, active, completed, archived |
| created_at | TEXT | Yes | Valid ISO 8601 timestamp |

### Learner

| Field | Type | Required | Validation |
|---|---|---|---|
| learner_id | TEXT | Yes | Primary key; unique and immutable |
| full_name | TEXT | Yes | Must not be empty |
| email | TEXT | Yes | Unique synthetic email address |
| status | TEXT | Yes | active, inactive, suspended |
| created_at | TEXT | Yes | Valid ISO 8601 timestamp |

### Assignment

| Field | Type | Required | Validation |
|---|---|---|---|
| assignment_id | TEXT | Yes | Primary key; format ASN-2026-000001 |
| course_id | TEXT | Yes | Must reference an existing course |
| title | TEXT | Yes | Must not be empty |
| description | TEXT | No | Optional text |
| published_at | TEXT | No | Required when status is published |
| due_at | TEXT | Yes | Valid timezone-aware timestamp |
| max_attempts | INTEGER | Yes | At least 1 |
| late_penalty_rate | REAL | Yes | Between 0 and 1 |
| status | TEXT | Yes | draft, published, closed, archived |
| created_at | TEXT | Yes | Valid ISO 8601 timestamp |

### Rubric

| Field | Type | Required | Validation |
|---|---|---|---|
| rubric_id | TEXT | Yes | Primary key; format RUB-<assignment-id>-01 |
| assignment_id | TEXT | Yes | Must reference an existing assignment |
| version | INTEGER | Yes | Positive integer; unique per assignment |
| title | TEXT | Yes | Must not be empty |
| total_points | REAL | Yes | Positive; must reconcile with criterion maxima |
| created_at | TEXT | Yes | Valid ISO 8601 timestamp |

### RubricCriterion

| Field | Type | Required | Validation |
|---|---|---|---|
| criterion_id | TEXT | Yes | Primary key; unique |
| rubric_id | TEXT | Yes | Must reference an existing rubric |
| criterion_name | TEXT | Yes | Unique within the rubric |
| description | TEXT | No | Optional text |
| max_points | REAL | Yes | Positive numeric value |
| weight | REAL | Yes | Positive numeric value |

### Submission

| Field | Type | Required | Validation |
|---|---|---|---|
| submission_id | TEXT | Yes | Primary key; deterministic identifier |
| assignment_id | TEXT | Yes | Must reference an existing assignment |
| learner_id | TEXT | Yes | Must reference an existing learner |
| attempt_number | INTEGER | Yes | Positive; unique per assignment and learner |
| submitted_at | TEXT | Yes | Valid timestamp |
| status | TEXT | Yes | submitted, late, missing, under_review, graded, returned, resubmitted, rejected |
| is_late | INTEGER | Yes | 0 or 1; derived from submission time and due date |
| created_at | TEXT | Yes | Valid ISO 8601 timestamp |

**Business rule:** A normal submission must belong to a learner enrolled in the assignment's course. Deliberate unenrolled-learner anomalies must be separately labelled and reported.

### SubmissionArtifact

| Field | Type | Required | Validation |
|---|---|---|---|
| artifact_id | TEXT | Yes | Primary key; unique |
| submission_id | TEXT | Yes | Must reference an existing submission |
| file_name | TEXT | Yes | Must not be empty |
| file_type | TEXT | No | File extension or MIME type |
| file_size_bytes | INTEGER | No | Non-negative when supplied |
| checksum_sha256 | TEXT | No | SHA-256 hex digest when supplied |
| storage_uri | TEXT | No | Synthetic or valid storage reference |
| artifact_status | TEXT | Yes | available, missing, unreadable, rejected |
| uploaded_at | TEXT | No | Valid timestamp when uploaded |

### Grade

| Field | Type | Required | Validation |
|---|---|---|---|
| grade_id | TEXT | Yes | Primary key; format GRD-<submission-id> for the initial grade |
| submission_id | TEXT | Yes | Must reference an existing submission |
| rubric_id | TEXT | Yes | Must reference the rubric used |
| version | INTEGER | Yes | Positive; unique per submission |
| raw_score | REAL | Yes | Non-negative and no greater than rubric maximum |
| late_penalty | REAL | Yes | Non-negative; applied according to policy at most once |
| final_score | REAL | Yes | Derived from raw score and penalty; never negative |
| graded_by | TEXT | Yes | Synthetic grader identifier |
| graded_at | TEXT | Yes | Valid timestamp |
| status | TEXT | Yes | draft, final, superseded |

**Business rule:** Criterion scores must not exceed their individual maximums. Their sum must reconcile with the raw grade, subject to the documented scoring policy. Grade revisions create new versions rather than overwriting prior grades.

### Feedback

| Field | Type | Required | Validation |
|---|---|---|---|
| feedback_id | TEXT | Yes | Primary key |
| grade_id | TEXT | Yes | Must reference an existing grade |
| feedback_text | TEXT | Yes | Must not be empty |
| feedback_type | TEXT | Yes | general, strength, improvement, private |
| created_by | TEXT | Yes | Synthetic instructor identifier |
| created_at | TEXT | Yes | Valid timestamp |

### Resubmission

| Field | Type | Required | Validation |
|---|---|---|---|
| resubmission_id | TEXT | Yes | Primary key |
| original_submission_id | TEXT | Yes | Must reference an existing submission |
| new_submission_id | TEXT | Yes | Must reference a different submission |
| requested_at | TEXT | Yes | Valid timestamp |
| decision | TEXT | Yes | pending, approved, rejected |
| decided_by | TEXT | No | Required when a decision is made |
| decided_at | TEXT | No | Required when a decision is made |
| reason | TEXT | No | Optional explanation |

**Business rule:** Resubmissions must respect the assignment's attempt limit and policy. Each attempt remains separately recorded.

### Appeal

| Field | Type | Required | Validation |
|---|---|---|---|
| appeal_id | TEXT | Yes | Primary key; format APP-2026-000001 |
| submission_id | TEXT | Yes | Must reference an existing submission |
| grade_id | TEXT | Yes | Must reference the grade being appealed |
| learner_id | TEXT | Yes | Must match the submission's learner |
| reason | TEXT | Yes | Must not be empty |
| filed_at | TEXT | Yes | Valid timestamp |
| status | TEXT | Yes | pending, under_review, upheld, rejected, grade_changed, withdrawn |
| decision | TEXT | No | Explanation of the outcome |
| decided_by | TEXT | No | Required when decided |
| decided_at | TEXT | No | Required when decided |
| revised_grade_id | TEXT | No | Required for a grade-change outcome |

## 3. Supporting tables

### Enrollment

Connects courses and learners in a many-to-many relationship. A learner can enroll in multiple courses, and each course can have multiple learners. The combination of course_id and learner_id must be unique.

### GradeCriterionScore

Records each criterion's score for a particular grade version. The score must be between zero and the criterion's maximum points. The grade and criterion must belong to compatible rubric versions.

### AuditEvent

Records an entity, action, prior value, new value, actor, timestamp, and reason. Grade changes and appeal decisions must be traceable.

### ValidationIssue

Records known or detected issues with an issue type, severity, description, expected outcome, detection timestamp, and resolution status.

## 4. Identifier conventions

- Course: `CRS-2026-000001`
- Learner: `LRN-2026-000001`
- Assignment: `ASN-2026-000001`
- Rubric: `RUB-<assignment-id>-01`
- Submission: `SUB-<assignment-id>-<learner-id>-01`
- Initial grade: `GRD-<submission-id>`
- Appeal: `APP-2026-000001`

Counters use six-digit zero padding where applicable. IDs must remain consistent across database records and exported files.

## 5. Data quality and acceptance rules

1. Primary keys are unique and immutable.
2. Foreign-key references resolve for valid baseline records.
3. Enrollment, publication, grading, resubmission, and appeal rules are respected.
4. Dates and lifecycle transitions are valid.
5. Scores, penalties, and totals reconcile with source records.
6. Late penalties are not applied twice.
7. Grade revisions and appeal outcomes preserve audit history.
8. Known anomalies have explicit ground-truth labels.
9. Ground truth is kept separate from input features.
10. A fixed random seed produces reproducible outputs.
11. CSV, JSON, and SQL exports are documented and validated.
12. Synthetic data is used unless external data has clearly documented lawful provenance and redistribution rights.