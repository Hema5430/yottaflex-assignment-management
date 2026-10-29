# YottaFlex Assignment Intelligence — Web App

A FastAPI + HTML/CSS/JavaScript web application added on top of the existing SQLite assignment-management project. It does not replace the original data-generation, validation, anomaly-detection, or export scripts.

## Features in this implementation

- Student workspace: view published assignments for enrolled courses, submit text work, view attempts/grades/feedback, request resubmissions, and appeal grades.
- Instructor workspace: review submissions, assign a rubric-bounded score with feedback, approve/reject resubmission requests, and uphold/reject appeals.
- Operations overview: database metrics and the existing deterministic anomaly detector.
- Audit timeline for key web workflow actions.
- AI assistant backed by Groq's hosted API when configured, with a basic deterministic fallback if no API key is set.
- Responsive HTML/CSS/JavaScript frontend; FastAPI JSON endpoints.
- Uses the existing `data/yottaflex.db`. Two small app-specific tables are created on startup to store submitted text and pending resubmission requests.

## Important demo limitation

The role switch and learner selection are for a local take-home demo, not production authentication. Do not deploy this app publicly with real learner data until proper authentication, authorization, CSRF protections, rate limits, and file handling are implemented. Synthetic learner records are used for the assignment.

## Setup

Use the existing Python 3.8 virtual environment. From the project root in PowerShell:

```powershell
python -m pip install -r requirements-web.txt
python -m uvicorn webapp.main:app --reload
```

Open http://127.0.0.1:8000.

Interactive API docs are at http://127.0.0.1:8000/docs.

## Optional Groq assistant

Create a key at https://console.groq.com/keys. The free plan has rate limits; check the current model catalog and your account's limits. Groq documents the OpenAI-compatible chat completion endpoint at `https://api.groq.com/openai/v1/chat/completions`.

In the same PowerShell terminal, set the key without committing it:

```powershell
$env:GROQ_API_KEY="YOUR_GROQ_API_KEY"
```

The default model is `openai/gpt-oss-20b`. If unavailable for your account, check the current Groq models list and set a model you can access:

```powershell
$env:GROQ_MODEL="openai/gpt-oss-20b"
```

Restart the server after changing environment variables. The app's AI assistant uses supplied application context and does not execute arbitrary SQL or change grades.

If no key is configured, the assistant returns a deterministic guidance message instead of failing.

## Verify

- Open `/api/health` and confirm `{"ok":true,"database":"connected"}`.
- Open `/api/overview` to inspect counts and anomaly findings.
- Open `/docs` to exercise the REST API.
- Run original tests in the original project environment:

```powershell
python -m unittest discover -s tests -v
```

## Data integrity and implementation notes

- Existing source-of-truth anomaly detection is reused from `src.detect_anomalies`.
- Grade submissions enforce the rubric maximum in the API.
- Submission, grading, appeal, and resubmission review actions create audit events.
- The app adds `app_submission_content` and `app_resubmission_requests`; these are separate from the original assignment schema.
- This is a take-home demo baseline, not production-ready multi-user software. Production hardening and role-based authentication remain necessary.
