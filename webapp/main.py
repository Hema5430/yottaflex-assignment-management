import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

# Load the local API key automatically when the application starts.
load_dotenv(ROOT / ".env")

DB_PATH = ROOT / "data" / "yottaflex.db"
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="YottaFlex Assignment Intelligence",
    description="Assignment workflow API and AI-assisted review",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id(prefix):
    return "{}-{}".format(prefix, uuid.uuid4().hex[:12].upper())


def connect():
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail="SQLite database not found at data/yottaflex.db")
    con = sqlite3.connect(str(DB_PATH), timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 10000")
    return con


def dict_rows(rows):
    return [dict(row) for row in rows]


def ensure_app_tables():
    with connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS app_submission_content (
                submission_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (submission_id) REFERENCES submissions(submission_id)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS app_resubmission_requests (
                request_id TEXT PRIMARY KEY,
                original_submission_id TEXT NOT NULL,
                learner_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','approved','rejected')),
                created_at TEXT NOT NULL,
                reviewed_at TEXT,
                reviewed_by TEXT,
                reviewer_note TEXT,
                new_submission_id TEXT,
                FOREIGN KEY (original_submission_id) REFERENCES submissions(submission_id),
                FOREIGN KEY (learner_id) REFERENCES learners(learner_id),
                FOREIGN KEY (new_submission_id) REFERENCES submissions(submission_id)
            )
        """)


@app.on_event("startup")
def startup():
    ensure_app_tables()


@app.get("/")
def home():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/health")
def health():
    try:
        with connect() as con:
            con.execute("SELECT 1")
        return {"ok": True, "database": "connected"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}


@app.get("/api/overview")
def overview():
    from src.detect_anomalies import detect_anomalies
    with connect() as con:
        metrics = {}
        for key, table in [
            ("courses", "courses"), ("learners", "learners"),
            ("assignments", "assignments"), ("submissions", "submissions"),
            ("grades", "grades"), ("appeals", "appeals"),
        ]:
            metrics[key] = con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
        metrics["pending_appeals"] = con.execute(
            "SELECT COUNT(*) FROM appeals WHERE status IN ('pending','under_review')"
        ).fetchone()[0]
        metrics["pending_resubmission_requests"] = con.execute(
            "SELECT COUNT(*) FROM app_resubmission_requests WHERE status='pending'"
        ).fetchone()[0]
    findings = detect_anomalies()
    return {
        "metrics": metrics,
        "findings": [
            {"issue_type": x[0], "entity_id": x[1], "description": x[2],
             "title": friendly_issue(x[0]), "severity": severity(x[0])}
            for x in findings
        ],
    }


def friendly_issue(issue_type):
    return {
        "unenrolled_learner_submission": "Submission without course enrollment",
        "grade_exceeds_rubric_maximum": "Grade exceeds rubric maximum",
        "duplicate_late_penalty": "Late penalty may have been applied twice",
        "appeal_without_audit_history": "Grade appeal is missing audit history",
    }.get(issue_type, issue_type.replace("_", " ").title())


def severity(issue_type):
    return "High" if issue_type in (
        "grade_exceeds_rubric_maximum", "appeal_without_audit_history"
    ) else "Medium"


@app.get("/api/learners")
def learners(search: str = "", limit: int = 25):
    limit = max(1, min(limit, 50))
    search = search.strip()
    with connect() as con:
        if search:
            pattern = "%" + search + "%"
            rows = con.execute("""
                SELECT learner_id, full_name, email, status
                FROM learners
                WHERE learner_id LIKE ? OR full_name LIKE ? OR email LIKE ?
                ORDER BY learner_id LIMIT ?
            """, (pattern, pattern, pattern, limit)).fetchall()
        else:
            rows = con.execute("""
                SELECT learner_id, full_name, email, status
                FROM learners ORDER BY learner_id LIMIT ?
            """, (limit,)).fetchall()
    return dict_rows(rows)


@app.get("/api/assignments")
def assignments(learner_id: str = "LRN-2026-000001", search: str = ""):
    with connect() as con:
        learner = con.execute(
            "SELECT learner_id FROM learners WHERE learner_id=?", (learner_id,)
        ).fetchone()
        if not learner:
            raise HTTPException(status_code=404, detail="Learner not found. Search and select a valid learner.")
        pattern = "%" + search.strip() + "%"
        rows = con.execute("""
            SELECT a.assignment_id, a.title, a.description, a.due_at,
                   a.max_attempts, a.status AS assignment_status,
                   c.course_id, c.course_name,
                   (SELECT COUNT(*) FROM submissions s
                    WHERE s.assignment_id=a.assignment_id AND s.learner_id=?) AS attempts_used,
                   (SELECT MAX(g.final_score) FROM submissions s
                    JOIN grades g ON g.submission_id=s.submission_id AND g.status='final'
                    WHERE s.assignment_id=a.assignment_id AND s.learner_id=?) AS latest_score,
                   (SELECT f.feedback_text FROM submissions s
                    JOIN grades g ON g.submission_id=s.submission_id AND g.status='final'
                    JOIN feedback f ON f.grade_id=g.grade_id
                    WHERE s.assignment_id=a.assignment_id AND s.learner_id=?
                    ORDER BY g.version DESC, f.created_at DESC LIMIT 1) AS latest_feedback
            FROM assignments a
            JOIN courses c ON c.course_id=a.course_id
            JOIN enrollments e ON e.course_id=a.course_id AND e.learner_id=?
                 AND e.status='enrolled'
            WHERE a.status='published' AND (a.title LIKE ? OR c.course_name LIKE ?)
            ORDER BY a.due_at ASC LIMIT 100
        """, (learner_id, learner_id, learner_id, learner_id, pattern, pattern)).fetchall()
    return dict_rows(rows)


@app.get("/api/submissions")
def submissions(learner_id: str = "LRN-2026-000001"):
    with connect() as con:
        rows = con.execute("""
            SELECT s.submission_id, s.assignment_id, a.title, c.course_name,
                   s.attempt_number, s.submitted_at, s.status, s.is_late,
                   g.grade_id, g.raw_score, g.late_penalty, g.final_score,
                   g.status AS grade_status, r.total_points AS rubric_maximum,
                   (SELECT GROUP_CONCAT(f.feedback_text, ' | ')
                    FROM feedback f WHERE f.grade_id=g.grade_id) AS feedback
            FROM submissions s
            JOIN assignments a ON a.assignment_id=s.assignment_id
            JOIN courses c ON c.course_id=a.course_id
            LEFT JOIN grades g ON g.submission_id=s.submission_id AND g.status='final'
            LEFT JOIN rubrics r ON r.rubric_id=g.rubric_id
            WHERE s.learner_id=?
            ORDER BY s.submitted_at DESC LIMIT 100
        """, (learner_id,)).fetchall()
    return dict_rows(rows)


class SubmissionIn(BaseModel):
    learner_id: str
    assignment_id: str
    content: str = Field(..., min_length=10, max_length=20000)


@app.post("/api/submissions")
def create_submission(body: SubmissionIn):
    stamp = now_iso()
    with connect() as con:
        learner = con.execute(
            "SELECT learner_id FROM learners WHERE learner_id=? AND status='active'",
            (body.learner_id,)
        ).fetchone()
        if not learner:
            raise HTTPException(status_code=404, detail="Active learner not found.")
        assignment = con.execute("""
            SELECT a.*, c.course_id FROM assignments a
            JOIN courses c ON c.course_id=a.course_id
            JOIN enrollments e ON e.course_id=a.course_id AND e.learner_id=?
                 AND e.status='enrolled'
            WHERE a.assignment_id=? AND a.status='published'
        """, (body.learner_id, body.assignment_id)).fetchone()
        if not assignment:
            raise HTTPException(status_code=403, detail="This assignment is not published for an active course enrollment.")
        attempt = con.execute("""
            SELECT COUNT(*) FROM submissions WHERE assignment_id=? AND learner_id=?
        """, (body.assignment_id, body.learner_id)).fetchone()[0]
        if attempt >= assignment["max_attempts"]:
            raise HTTPException(status_code=400, detail="Maximum attempts reached for this assignment.")
        attempt_number = attempt + 1
        submission_id = "SUB-WEB-" + uuid.uuid4().hex[:12].upper()
        late = int(datetime.now(timezone.utc) > datetime.fromisoformat(
            assignment["due_at"].replace("Z", "+00:00")
        ))
        status = "late" if late else "submitted"
        con.execute("""
            INSERT INTO submissions
            (submission_id, assignment_id, learner_id, attempt_number,
             submitted_at, status, is_late, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (submission_id, body.assignment_id, body.learner_id,
              attempt_number, stamp, status, late, stamp))
        con.execute("""
            INSERT INTO app_submission_content(submission_id, content, created_at)
            VALUES (?, ?, ?)
        """, (submission_id, body.content.strip(), stamp))
        con.execute("""
            INSERT INTO audit_events
            (event_id, entity_type, entity_id, action, old_value, new_value,
             actor_id, occurred_at, reason)
            VALUES (?, 'Submission', ?, 'submitted', NULL, ?, ?, ?, ?)
        """, (new_id("AUD-WEB"), submission_id, status, body.learner_id,
              stamp, "Submission created through the YottaFlex web application."))
    return {"ok": True, "submission_id": submission_id, "attempt_number": attempt_number, "status": status}


class ResubmissionRequestIn(BaseModel):
    learner_id: str
    original_submission_id: str
    reason: str = Field(..., min_length=5, max_length=1000)


@app.post("/api/resubmission-requests")
def request_resubmission(body: ResubmissionRequestIn):
    stamp = now_iso()
    with connect() as con:
        original = con.execute("""
            SELECT s.*, a.max_attempts FROM submissions s
            JOIN assignments a ON a.assignment_id=s.assignment_id
            WHERE s.submission_id=? AND s.learner_id=?
        """, (body.original_submission_id, body.learner_id)).fetchone()
        if not original:
            raise HTTPException(status_code=404, detail="Submission not found for this learner.")
        if original["attempt_number"] >= original["max_attempts"]:
            raise HTTPException(status_code=400, detail="No attempts remain for this assignment.")
        pending = con.execute("""
            SELECT 1 FROM app_resubmission_requests
            WHERE original_submission_id=? AND status='pending'
        """, (body.original_submission_id,)).fetchone()
        if pending:
            raise HTTPException(status_code=409, detail="A resubmission request is already pending.")
        request_id = new_id("RSQ")
        con.execute("""
            INSERT INTO app_resubmission_requests
            (request_id, original_submission_id, learner_id, reason, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
        """, (request_id, body.original_submission_id, body.learner_id, body.reason.strip(), stamp))
    return {"ok": True, "request_id": request_id, "status": "pending"}


@app.get("/api/instructor/queue")
def instructor_queue():
    with connect() as con:
        rows = con.execute("""
            SELECT s.submission_id, s.assignment_id, a.title, c.course_name,
                   l.learner_id, l.full_name, s.attempt_number, s.submitted_at,
                   s.status, s.is_late,
                   (SELECT COUNT(*) FROM grades g WHERE g.submission_id=s.submission_id
                    AND g.status='final') AS final_grade_count,
                   g.final_score, r.total_points AS rubric_maximum
            FROM submissions s
            JOIN assignments a ON a.assignment_id=s.assignment_id
            JOIN courses c ON c.course_id=a.course_id
            JOIN learners l ON l.learner_id=s.learner_id
            LEFT JOIN grades g ON g.submission_id=s.submission_id AND g.status='final'
            LEFT JOIN rubrics r ON r.rubric_id=g.rubric_id
            WHERE s.status IN ('submitted','late','resubmitted','under_review','returned')
            ORDER BY s.is_late DESC, s.submitted_at DESC LIMIT 200
        """).fetchall()
        requests = con.execute("""
            SELECT rr.request_id, rr.original_submission_id, rr.learner_id,
                   l.full_name, a.title, rr.reason, rr.created_at, rr.status
            FROM app_resubmission_requests rr
            JOIN submissions s ON s.submission_id=rr.original_submission_id
            JOIN assignments a ON a.assignment_id=s.assignment_id
            JOIN learners l ON l.learner_id=rr.learner_id
            WHERE rr.status='pending' ORDER BY rr.created_at
        """).fetchall()
        appeals = con.execute("""
            SELECT ap.appeal_id, ap.submission_id, ap.learner_id, l.full_name,
                   a.title, ap.reason, ap.filed_at, ap.status, g.final_score
            FROM appeals ap
            JOIN submissions s ON s.submission_id=ap.submission_id
            JOIN assignments a ON a.assignment_id=s.assignment_id
            JOIN learners l ON l.learner_id=ap.learner_id
            LEFT JOIN grades g ON g.grade_id=ap.grade_id
            WHERE ap.status IN ('pending','under_review')
            ORDER BY ap.filed_at LIMIT 100
        """).fetchall()
    return {"submissions": dict_rows(rows), "resubmission_requests": dict_rows(requests), "appeals": dict_rows(appeals)}


class GradeIn(BaseModel):
    submission_id: str
    graded_by: str = "INS-DEMO-001"
    raw_score: float = Field(..., ge=0)
    feedback: str = Field(..., min_length=3, max_length=5000)


@app.post("/api/grades")
def grade_submission(body: GradeIn):
    stamp = now_iso()
    with connect() as con:
        submission = con.execute("""
            SELECT s.*, r.rubric_id, r.total_points
            FROM submissions s JOIN rubrics r ON r.assignment_id=s.assignment_id
            WHERE s.submission_id=?
            ORDER BY r.version DESC LIMIT 1
        """, (body.submission_id,)).fetchone()
        if not submission:
            raise HTTPException(status_code=404, detail="Submission or rubric not found.")
        if body.raw_score > submission["total_points"]:
            raise HTTPException(status_code=400, detail="Score cannot exceed rubric maximum of {}.".format(submission["total_points"]))
        old = con.execute("""
            SELECT * FROM grades WHERE submission_id=? AND status='final'
            ORDER BY version DESC LIMIT 1
        """, (body.submission_id,)).fetchone()
        version = 1
        if old:
            version = old["version"] + 1
            con.execute("UPDATE grades SET status='superseded' WHERE grade_id=?", (old["grade_id"],))
        penalty = round(body.raw_score * 0, 2)
        final_score = max(0, body.raw_score - penalty)
        grade_id = new_id("GRD-WEB")
        con.execute("""
            INSERT INTO grades
            (grade_id, submission_id, rubric_id, version, raw_score, late_penalty,
             final_score, graded_by, graded_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'final')
        """, (grade_id, body.submission_id, submission["rubric_id"], version,
              body.raw_score, penalty, final_score, body.graded_by, stamp))
        feedback_id = new_id("FDB-WEB")
        con.execute("""
            INSERT INTO feedback
            (feedback_id, grade_id, feedback_text, feedback_type, created_by, created_at)
            VALUES (?, ?, ?, 'general', ?, ?)
        """, (feedback_id, grade_id, body.feedback.strip(), body.graded_by, stamp))
        con.execute("UPDATE submissions SET status='graded' WHERE submission_id=?", (body.submission_id,))
        con.execute("""
            INSERT INTO audit_events
            (event_id, entity_type, entity_id, action, old_value, new_value,
             actor_id, occurred_at, reason)
            VALUES (?, 'Grade', ?, 'grade_revised', ?, ?, ?, ?, ?)
        """, (new_id("AUD-WEB"), body.submission_id,
              str(old["final_score"]) if old else None, str(final_score),
              body.graded_by, stamp, "Grade recorded through instructor review workflow."))
    return {"ok": True, "grade_id": grade_id, "final_score": final_score, "version": version}


class AppealIn(BaseModel):
    learner_id: str
    submission_id: str
    reason: str = Field(..., min_length=10, max_length=2000)


@app.post("/api/appeals")
def create_appeal(body: AppealIn):
    stamp = now_iso()
    with connect() as con:
        grade = con.execute("""
            SELECT g.grade_id FROM grades g JOIN submissions s ON s.submission_id=g.submission_id
            WHERE s.submission_id=? AND s.learner_id=? AND g.status='final'
            ORDER BY g.version DESC LIMIT 1
        """, (body.submission_id, body.learner_id)).fetchone()
        if not grade:
            raise HTTPException(status_code=404, detail="No final grade found for this learner's submission.")
        exists = con.execute("""
            SELECT 1 FROM appeals WHERE submission_id=? AND learner_id=?
              AND status IN ('pending','under_review')
        """, (body.submission_id, body.learner_id)).fetchone()
        if exists:
            raise HTTPException(status_code=409, detail="An appeal is already pending for this submission.")
        appeal_id = new_id("APP-WEB")
        con.execute("""
            INSERT INTO appeals
            (appeal_id, submission_id, grade_id, learner_id, reason, filed_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (appeal_id, body.submission_id, grade["grade_id"], body.learner_id, body.reason.strip(), stamp))
        con.execute("""
            INSERT INTO audit_events
            (event_id, entity_type, entity_id, action, old_value, new_value,
             actor_id, occurred_at, reason)
            VALUES (?, 'Appeal', ?, 'filed', NULL, 'pending', ?, ?, ?)
        """, (new_id("AUD-WEB"), appeal_id, body.learner_id, stamp, "Appeal filed through web application."))
    return {"ok": True, "appeal_id": appeal_id, "status": "pending"}


class AppealDecisionIn(BaseModel):
    status: str
    decision: str = Field(..., min_length=3, max_length=2000)
    decided_by: str = "INS-DEMO-001"


@app.post("/api/instructor/appeals/{appeal_id}/decision")
def decide_appeal(appeal_id: str, body: AppealDecisionIn):
    allowed = {"upheld", "rejected"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail="Choose upheld or rejected. Grade changes must use the grade-review workflow.")
    stamp = now_iso()
    with connect() as con:
        appeal = con.execute("SELECT * FROM appeals WHERE appeal_id=?", (appeal_id,)).fetchone()
        if not appeal:
            raise HTTPException(status_code=404, detail="Appeal not found.")
        con.execute("""
            UPDATE appeals SET status=?, decision=?, decided_by=?, decided_at=?
            WHERE appeal_id=?
        """, (body.status, body.decision.strip(), body.decided_by, stamp, appeal_id))
        con.execute("""
            INSERT INTO audit_events
            (event_id, entity_type, entity_id, action, old_value, new_value,
             actor_id, occurred_at, reason)
            VALUES (?, 'Appeal', ?, 'decision_recorded', ?, ?, ?, ?, ?)
        """, (new_id("AUD-WEB"), appeal_id, appeal["status"], body.status,
              body.decided_by, stamp, body.decision.strip()))
    return {"ok": True, "appeal_id": appeal_id, "status": body.status}


class ResubmissionDecisionIn(BaseModel):
    status: str
    reviewer_note: str = ""
    reviewed_by: str = "INS-DEMO-001"


@app.post("/api/instructor/resubmissions/{request_id}/decision")
def decide_resubmission(request_id: str, body: ResubmissionDecisionIn):
    if body.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be approved or rejected.")
    stamp = now_iso()
    with connect() as con:
        req = con.execute("""
            SELECT rr.*, s.assignment_id, s.attempt_number, s.submitted_at,
                   a.max_attempts, a.due_at
            FROM app_resubmission_requests rr
            JOIN submissions s ON s.submission_id=rr.original_submission_id
            JOIN assignments a ON a.assignment_id=s.assignment_id
            WHERE rr.request_id=?
        """, (request_id,)).fetchone()
        if not req:
            raise HTTPException(status_code=404, detail="Resubmission request not found.")
        if req["status"] != "pending":
            raise HTTPException(status_code=409, detail="This request has already been reviewed.")
        new_submission_id = None
        if body.status == "approved":
            if req["attempt_number"] >= req["max_attempts"]:
                raise HTTPException(status_code=400, detail="Maximum attempts reached.")
            attempt = req["attempt_number"] + 1
            new_submission_id = "SUB-WEB-" + uuid.uuid4().hex[:12].upper()
            con.execute("""
                INSERT INTO submissions
                (submission_id, assignment_id, learner_id, attempt_number,
                 submitted_at, status, is_late, created_at)
                VALUES (?, ?, ?, ?, ?, 'submitted', 0, ?)
            """, (new_submission_id, req["assignment_id"], req["learner_id"], attempt, stamp, stamp))
            con.execute("""
                INSERT INTO app_submission_content(submission_id, content, created_at)
                VALUES (?, ?, ?)
            """, (new_submission_id, "Resubmission draft: learner should upload revised work.", stamp))
            res_id = new_id("RES-WEB")
            con.execute("""
                INSERT INTO resubmissions
                (resubmission_id, original_submission_id, new_submission_id,
                 requested_at, decision, decided_by, decided_at, reason)
                VALUES (?, ?, ?, ?, 'approved', ?, ?, ?)
            """, (res_id, req["original_submission_id"], new_submission_id,
                  req["created_at"], body.reviewed_by, stamp, req["reason"]))
        con.execute("""
            UPDATE app_resubmission_requests
            SET status=?, reviewed_at=?, reviewed_by=?, reviewer_note=?, new_submission_id=?
            WHERE request_id=?
        """, (body.status, stamp, body.reviewed_by, body.reviewer_note,
              new_submission_id, request_id))
        con.execute("""
            INSERT INTO audit_events
            (event_id, entity_type, entity_id, action, old_value, new_value,
             actor_id, occurred_at, reason)
            VALUES (?, 'ResubmissionRequest', ?, 'decision_recorded', 'pending', ?, ?, ?, ?)
        """, (new_id("AUD-WEB"), request_id, body.status, body.reviewed_by,
              stamp, body.reviewer_note or req["reason"]))
    return {"ok": True, "request_id": request_id, "status": body.status,
            "new_submission_id": new_submission_id}


@app.get("/api/ai/status")
def ai_status():
    return {"provider": "Groq", "configured": bool(os.getenv("GROQ_API_KEY"))}


class ChatIn(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)
    context: Optional[dict] = None


@app.post("/api/ai/chat")
def ai_chat(body: ChatIn):
    key = os.getenv("GROQ_API_KEY")

    if not key:
        return {
            "provider": "rule-based fallback",
            "answer": (
                "The AI provider is not configured. "
                "Python still checks enrollment, rubric limits, "
                "late penalties, and audit history."
            ),
        }

    model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    context = body.context or {}

    prompt = (
        "You are YottaFlex Assignment Assistant. Explain only from "
        "the supplied application context. Do not invent records, "
        "make grading decisions, execute SQL, or claim to change data. "
        "If context is insufficient, ask for clarification. "
        "Be helpful to students and instructors.\n\n"
        "Application context:\n"
        + json.dumps(context, ensure_ascii=False, default=str)
        + "\n\nUser question:\n"
        + body.question
    )

    try:
        from groq import Groq

        client = Groq(api_key=key)

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful education workflow assistant. "
                        "Evidence first; no grade changes."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=700,
        )

        answer = response.choices[0].message.content

        return {
            "provider": "Groq",
            "model": model_name,
            "answer": answer or "The AI provider returned an empty response.",
        }

    except Exception as exc:
        status_code = getattr(exc, "status_code", None)

        if status_code:
            raise HTTPException(
                status_code=502,
                detail="Groq API error {}: {}".format(
                    status_code, str(exc)[:1200]
                ),
            )

        raise HTTPException(
            status_code=502,
            detail="AI request failed: {}".format(str(exc)[:1200]),
        )


@app.get("/api/audit")
def audit(limit: int = 50):
    limit = max(1, min(limit, 200))
    with connect() as con:
        rows = con.execute("""
            SELECT event_id, entity_type, entity_id, action, old_value,
                   new_value, actor_id, occurred_at, reason
            FROM audit_events ORDER BY occurred_at DESC LIMIT ?
        """, (limit,)).fetchall()
    return dict_rows(rows)
