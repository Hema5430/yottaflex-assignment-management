# YottaFlex.ai — AI-Powered Assignment Management & Anomaly Intelligence

An assignment-management application that combines academic workflows, grading validation, deterministic anomaly detection, and **LLM-powered explanations** to help reviewers understand suspicious or inconsistent records and decide what to investigate next.

## Project Overview

YottaFlex.ai is designed to support the assignment lifecycle, from learner submissions to grading, feedback, resubmissions, appeals, and audit history. It also identifies potential data-quality and grading anomalies using explicit Python business rules.

The application integrates a Large Language Model (LLM) to turn detected anomalies into understandable explanations and suggested reviewer actions.

**Core design principle:** Business-rule decisions remain deterministic and verifiable in Python. The LLM provides explanations; it does not independently decide whether an anomaly exists.

## Key Features

### 1. Assignment Management

- Learner assignment submissions.
- Submission and grading workflows.
- Grading feedback and revision history.
- Resubmission requests and approval workflows.
- Grade appeals and review tracking.
- Audit events for relevant workflow actions.
- SQLite-backed persistence for application records.

### 2. Deterministic Anomaly Detection

The anomaly detection engine applies explicit business rules to identify suspicious records. Its findings can be inspected and validated against known anomaly scenarios.

Examples include:

- **Unenrolled learner submission:** A submission exists for a learner who is not enrolled in the corresponding course.
- **Grade exceeds rubric maximum:** A recorded grade or criterion score violates the configured rubric limit.
- **Duplicate late penalty:** A late penalty may have been applied more than once.
- **Appeal without audit history:** An appeal is missing the expected audit trail.

The detector produces structured findings for review instead of relying on an LLM to make the underlying business decision.

### 3. LLM-Powered Anomaly Explanation — AI Highlight

The application integrates the Groq API and an LLM to make anomaly findings easier to understand and act upon.

Rather than using the LLM as an unrestricted anomaly classifier, the application uses it as an **explanation and reviewer-assistance layer**.

The AI assistant is intended to help reviewers understand:

- **What happened:** A clear, human-readable explanation of the detected issue.
- **Which business rule is relevant:** The rule or expected condition associated with the finding.
- **Why it matters:** The potential impact on grading integrity, workflow consistency, or data quality.
- **What to investigate next:** Suggested evidence checks and reviewer actions.
- **How to communicate the finding:** A concise explanation that helps technical and non-technical reviewers understand the issue.

For example, if a grade exceeds the maximum allowed by a rubric, the deterministic detector identifies the violation. The LLM can then explain that the score exceeds the permitted maximum and suggest checking the rubric configuration, criterion-level scores, and grading records before approving a correction.

#### AI architecture and responsible use

The AI integration follows a separation-of-responsibilities approach:

1. **Data layer:** SQLite stores assignment, submission, grading, appeal, and audit records.
2. **Rule-based detection layer:** Python checks records against explicit business rules.
3. **AI explanation layer:** The Groq API sends the relevant question and application context to the configured LLM.
4. **Reviewer layer:** The reviewer uses the explanation and suggested actions to investigate the finding.

The LLM does not replace the deterministic validation logic or automatically authorize grade changes. Reviewers remain responsible for decisions requiring investigation or correction.

**Configured model:** `openai/gpt-oss-20b`  
**LLM provider:** Groq API  
**Integration:** Python Groq SDK

The model is configured through environment variables so credentials are not hardcoded into application source code.

### 4. Data Integrity and Validation

The project includes scripts for generating synthetic data, creating workflow scenarios, injecting known anomalies, exporting data, and validating database integrity.

Validation covers:

- Expected record counts for the baseline generated dataset.
- Foreign-key integrity.
- Unexpected invalid grades.
- Submissions from unenrolled learners.
- Workflow consistency, including resubmissions, appeals, and audit events.
- Known anomaly scenarios and their expected findings.

The data validator distinguishes the original synthetic dataset from injected anomalies and website-created submissions when checking baseline record counts.

### 5. Data Export and Inspection

The project includes CSV, JSON, and SQL exports for supported database entities, along with utilities for inspecting records and anomaly findings.

Exports are useful for reviewing the generated dataset, debugging validation issues, and inspecting the output of the application.

## Technology Stack

| Component | Technologies |
|---|---|
| Programming language | Python |
| Web application | FastAPI, Uvicorn |
| Additional UI | Streamlit components and Python UI modules |
| Database | SQLite |
| AI integration | Groq API, Groq Python SDK |
| Language model | OpenAI GPT-OSS 20B, accessed through Groq |
| Frontend | HTML, CSS, JavaScript |
| Data processing | Python, CSV, JSON, SQL |
| Testing and validation | pytest, custom validation scripts |
| Development tools | VS Code, Git, GitHub |

## Project Structure

```text
yottaflex-assignment-management/
├── app.py
├── src/
│   ├── database.py
│   ├── schema.sql
│   ├── generate_data.py
│   ├── generate_workflows.py
│   ├── inject_anomalies.py
│   ├── detect_anomalies.py
│   ├── inspect_anomalies.py
│   ├── export_data.py
│   ├── app_queries.py
│   ├── validate_data.py
│   ├── validate_workflows.py
│   └── check_database.py
├── webapp/
│   ├── main.py
│   └── static/
│       ├── index.html
│       ├── styles.css
│       └── app.js
├── ui/
│   ├── staff.py
│   └── student.py
├── tests/
│   └── test_schema.py
├── docs/
│   └── data_dictionary.md
├── exports/
├── requirements.txt
├── requirements-web.txt
├── README.md
└── README_WEBAPP.md
```

## Getting Started

### Prerequisites

- Python 3.8 or a compatible version supported by the installed dependencies.
- Git.
- A Groq API key for the LLM explanation feature.

### 1. Clone the repository

```bash
git clone https://github.com/Hema5430/yottaflex-assignment-management.git
cd yottaflex-assignment-management
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the appropriate execution policy for your session.

### 3. Install dependencies

Install the base dependencies:

```powershell
python -m pip install -r requirements.txt
```

Install the additional web application dependencies:

```powershell
python -m pip install -r requirements-web.txt
```

### 4. Configure the LLM API key

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b
```

Replace the placeholder with your own API key. Never commit `.env` to GitHub or include API keys in screenshots, source code, or logs.

### 5. Initialize or prepare the database

The project uses SQLite. Follow the setup instructions in `README_WEBAPP.md` and the database utilities in `src/` to prepare the database.

If you regenerate the synthetic dataset, review the generator and anomaly-injection scripts first. Do not regenerate or overwrite an existing database containing records you want to preserve.

### 6. Start the FastAPI application

From the project root:

```powershell
python -m uvicorn webapp.main:app --reload
```

Open the following addresses in your browser:

- Application: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health
- AI configuration status: http://127.0.0.1:8000/api/ai/status

The AI feature requires a valid API key and network access to the Groq service.

### 7. Run the Streamlit interface

If using the Streamlit interface, start it with:

```powershell
python -m streamlit run app.py
```

## Validation and Testing

Run the data-integrity checks:

```powershell
python -m src.validate_data
```

Run the workflow validation:

```powershell
python -m src.validate_workflows
```

Run the automated tests:

```powershell
python -m pytest -q
```

The project has passed the data-validation checks, and the workflow validation checks passed during development. Run the commands in your own environment to verify the current database and code.

## Engineering Decisions

### Deterministic rules plus LLM explanations

The application separates detection from interpretation. This keeps business-rule findings reproducible and makes the explanation layer easier to evaluate independently.

### SQLite for persistence

SQLite provides a lightweight database suitable for a self-contained assignment-management project without requiring a separate database server.

### Auditability and validation

Workflow checks, audit events, known anomaly scenarios, and structured exports help make the application easier to inspect and debug.

### Environment-based configuration

API credentials and model configuration are supplied through environment variables rather than being embedded in source code.

## Current Scope and Limitations

- The project is a demonstration application, not a production-ready academic platform.
- The demonstration role switch is not a substitute for production authentication and authorization.
- LLM-generated explanations can be incomplete or incorrect and should be reviewed before action is taken.
- The LLM does not independently validate business rules or guarantee that an anomaly is genuine.
- Production deployment would require appropriate authentication, authorization, input validation, secret management, monitoring, and privacy controls.
- API availability, rate limits, and model access depend on the configured provider.

## Future Improvements

- Add production-grade authentication and role-based access control.
- Add more anomaly rules and regression tests.
- Improve the presentation of AI explanations and supporting evidence.
- Add structured logging, monitoring, and error handling for LLM requests.
- Introduce reviewer feedback to evaluate explanation quality.
- Expand automated tests for API endpoints and end-to-end workflows.

## Author

**Hema Sri**

AI and Machine Learning | Python | Data Engineering | LLM Integration

GitHub: [Hema5430](https://github.com/Hema5430)

---

*Built as an assignment-management and data-quality intelligence project, combining deterministic validation with LLM-assisted explanations for human review.*
