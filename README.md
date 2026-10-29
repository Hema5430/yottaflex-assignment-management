# YottaFlex.ai — Assignment Management Data Pipeline

## 1. Project Overview

This project implements a reproducible, database-driven assignment management pipeline for an educational platform. It models the assignment lifecycle, including assignment publication, learner submissions, rubric-based grading, feedback, resubmissions, late penalties, appeals, and grade revisions.

The pipeline uses Python and SQLite to generate synthetic data, enforce data-quality checks, detect intentionally injected anomalies, validate workflow history, and export datasets in CSV, JSON, and SQL formats.

## 2. Objectives

- Build a relational data model with primary keys, foreign keys, and relationships between entities.
- Generate deterministic synthetic data using a fixed random seed.
- Validate data integrity and workflow consistency.
- Detect predefined data anomalies using explicit business rules.
- Preserve grade revisions, appeals, and audit history.
- Export database tables for inspection and downstream analysis.
- Make the pipeline reproducible and easy to execute locally.

## 3. Technology Stack

- **Language:** Python
- **Database:** SQLite
- **Data formats:** CSV, JSON, SQL
- **Testing:** Python `unittest`
- **Dependencies:** Python standard library

No third-party Python packages are required for the current implementation.

## 4. Data Model

The database represents the main entities involved in assignment management, including:

- Courses
- Learners
- Enrollments
- Assignments
- Rubrics and rubric criteria
- Submissions and submission artifacts
- Grades and grade revisions
- Feedback
- Resubmission requests
- Appeals
- Audit events
- Validation issues

Primary and foreign keys connect related records and help preserve referential integrity. Grade revisions and audit events provide a history of relevant workflow changes.

## 5. Synthetic Dataset

The pipeline uses a deterministic seed of `20261022` to support repeatable data generation.

The expected baseline dataset contains:

| Entity | Expected count |
|---|---:|
| Courses | 50 |
| Learners | 10,000 |
| Assignments | 1,000 |
| Original submissions | 30,000 |
| Original submission artifacts | 30,000 |
| Original grades | 30,000 |
| Original feedback records | 30,000 |

The final database also contains workflow records and intentionally injected anomaly cases. Therefore, final table counts may differ from the baseline counts shown above.

## 6. Anomaly Detection

The pipeline injects and detects four predefined anomaly categories:

1. **Submission by an unenrolled learner:** A learner submits work for a course in which they are not enrolled.
2. **Grade exceeding the rubric maximum:** A recorded score exceeds the maximum allowed by the rubric.
3. **Duplicate late penalty:** A late penalty is applied more than once.
4. **Appeal without audit history:** An appeal changes a grade without the required audit event.

The detection logic uses SQL queries and explicit business rules. These cases are intentionally introduced for validation and demonstration; they should not be interpreted as naturally occurring production incidents.

## 7. Project Structure

```text
yottaflex-project/
├── src/
│   ├── main.py
│   ├── generate_data.py
│   ├── inject_anomalies.py
│   ├── detect_anomalies.py
│   ├── validate_data.py
│   ├── validate_workflows.py
│   └── export_data.py
├── tests/
├── data/
├── exports/
├── docs/
├── backups/
├── .gitignore
├── requirements.txt
└── README.md
```

The exact files may vary slightly depending on the final packaged version. Generated databases and backups should not be committed unless they are intentionally included as documented sample artifacts.

## 8. Setup and Execution

### Prerequisites

- Python 3.8 or later
- Git (optional, for version control)

### Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks virtual-environment activation, use the environment's Python executable directly.

### Install dependencies

The current implementation uses only the Python standard library, so installing external packages is not required.

### Run the pipeline

From the project root directory:

```powershell
python -m src.main
```

The pipeline runs the available generation, anomaly-injection, validation, detection, and export steps.

**Important:** Run the full generation pipeline on a fresh or backed-up database when rebuilding the dataset. Do not rerun data-generation or anomaly-injection steps against an existing database unless the scripts explicitly support safe repeated execution.

### Run automated tests

```powershell
python -m unittest discover -s tests -v
```

The tests cover database structure, baseline data counts, anomaly scenarios, resubmissions, appeals, and audit history.

## 9. Outputs

The pipeline produces:

- A SQLite database containing generated records and workflow history.
- CSV exports of database tables.
- JSON exports of database tables.
- An SQL export for inspection or reconstruction, depending on the export implementation.
- Validation and anomaly-detection results printed during execution.

Generated files are stored in the project's `data/` and `exports/` directories.

## 10. Validation

Validation checks cover:

- Expected baseline record counts
- Primary-key uniqueness and foreign-key integrity
- Enrollment and submission consistency
- Rubric score limits and grade reconciliation
- Workflow and lifecycle consistency
- Resubmission and appeal relationships
- Audit-history requirements
- Detection of the four predefined anomaly categories

Intentional anomaly cases are documented separately from ordinary data-integrity checks so that the pipeline can demonstrate detection without treating the test scenarios as valid production records.

## 11. Reproducibility

The fixed seed `20261022` supports deterministic synthetic data generation. For a reproducible run:

1. Start from a fresh database or the documented clean starting state.
2. Run the pipeline from the project root.
3. Execute the automated tests.
4. Review the generated exports and validation output.

Reproducibility depends on the generation and injection scripts being deterministic and safe to rerun only under their documented conditions.

## 12. Limitations and Future Improvements

- The dataset is synthetic and does not represent real learner information.
- Anomaly detection is rule-based and limited to the explicitly implemented checks.
- The project uses SQLite for local execution rather than a production database service.
- Further improvements could include broader edge-case testing, richer audit validation, a reviewer interface, and optional AI-generated explanations of detected anomalies.

## 13. Responsible Use of AI

AI assistance was used during project development and documentation. The data generation, database operations, validation, and anomaly-detection behavior should be understood through the submitted source code and tests. Any AI-generated explanation should remain separate from the deterministic detection result and should not replace business-rule validation.

## 14. Author and Submission Notes

This project was prepared as a take-home assignment for the Associate AI Forward Deployed Engineer role at YottaFlex.ai.

Before submission, verify that the repository contains the final source code, tests, documentation, required exports, and any requested prompt history. Do not include virtual environments, secrets, temporary diagnostic scripts, or unnecessary backups.
