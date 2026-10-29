import json
import os

import pandas as pd
import streamlit as st
import urllib.request
import urllib.error

from src.app_queries import (
    get_anomaly_evidence,
    get_anomaly_findings,
    get_dashboard_metrics,
    get_dataset_summary,
)

st.set_page_config(
    page_title="YottaFlex AI | Assignment Intelligence",
    page_icon="🎓",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.7rem; padding-bottom: 2rem;}
    [data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.08);
        padding: 14px 16px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.18);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🎓 YottaFlex AI")
st.caption("Assignment Intelligence · Data quality, anomaly investigation, and AI-assisted explanations")

def get_api_key():
    """Read the Gemini key without triggering a missing-secrets warning."""
    key = os.getenv("GEMINI_API_KEY", "")
    if key:
        return key

    secrets_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        ".streamlit",
        "secrets.toml",
    )

    if os.path.isfile(secrets_path):
        try:
            return st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            return ""

    return ""


def explain_with_gemini(api_key, task, evidence):
    """Generate an explanation using the Gemini REST API."""
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    prompt = f"""
You are YottaFlex AI, an assistant for assignment-management data.

Use only the supplied evidence. Do not invent facts.
Distinguish observed evidence from recommendations.
Never modify grades or database records.
If evidence is insufficient, say so.

Task from reviewer:
{task}

Database evidence (JSON):
{json.dumps(evidence, indent=2, default=str)}
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + model
        + ":generateContent?key="
        + api_key
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2
        }
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))

        return result["candidates"][0]["content"]["parts"][0]["text"]

    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Gemini API error ({exc.code}): {details}"
        ) from exc

try:
    metrics = get_dashboard_metrics()
    findings = get_anomaly_findings()
    dataset_summary = get_dataset_summary()
except Exception as exc:
    st.error("The application could not read the existing SQLite database.")
    st.code(str(exc))
    st.info("Confirm that data/yottaflex.db exists and that you launched Streamlit from the project root.")
    st.stop()

with st.sidebar:
    st.header("Workspace")
    st.success("SQLite database connected")
    st.caption("The existing data-generation pipeline is not run by this app.")
    st.divider()
    st.markdown("**AI provider**")
    st.write("Google Gemini")
    if get_api_key():
        st.success("API key configured")
    else:
        st.warning("API key not configured")
        st.caption("Dashboard and rule-based anomaly detection still work. Add GEMINI_API_KEY to enable explanations.")

tab_dashboard, tab_investigator, tab_ask = st.tabs(
    ["📊 Overview", "🔎 Anomaly Investigator", "💬 Ask YottaFlex AI"]
)

with tab_dashboard:
    st.subheader("Assignment operations at a glance")
    metric_order = [
        ("Courses", "courses"),
        ("Learners", "learners"),
        ("Assignments", "assignments"),
        ("Submissions", "submissions"),
        ("Grades", "grades"),
        ("Appeals", "appeals"),
    ]
    cols = st.columns(6)
    for col, (label, key) in zip(cols, metric_order):
        col.metric(label, f"{metrics.get(key, 0):,}")

    st.divider()
    left, right = st.columns([1.3, 1])
    with left:
        st.markdown("#### Detected data-quality findings")
        if findings:
            df = pd.DataFrame(
                findings,
                columns=["Issue type", "Entity ID", "Rule-based description"],
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.success("No anomalies were detected by the current rules.")
    with right:
        st.markdown("#### What this means")
        st.write(
            "Python and SQL remain responsible for detecting anomalies. "
            "Gemini is used only to explain evidence and suggest reviewer actions."
        )
        st.info(
            "These are synthetic assignment-management records and intentionally "
            "injected test anomalies, not real learner incidents."
        )

with tab_investigator:
    st.subheader("Investigate a detected anomaly")
    if not findings:
        st.success("No anomalies were returned by the current detection rules.")
    else:
        options = [
            f"{issue_type} · {entity_id}"
            for issue_type, entity_id, description in findings
        ]
        selected_label = st.selectbox("Select a finding", options)
        selected_index = options.index(selected_label)
        issue_type, entity_id, description = findings[selected_index]
        evidence = get_anomaly_evidence(issue_type, entity_id)

        st.markdown(f"**Rule-based finding:** `{issue_type}`")
        st.write(description)
        with st.expander("View source evidence", expanded=True):
            st.json(evidence)

        reviewer_context = st.text_area(
            "Optional question for Gemini",
            placeholder="Example: Explain why this violates the business rule and what a reviewer should check.",
            key="investigator_question",
        )
        if st.button("✨ Explain this finding", type="primary", key="explain_finding"):
            api_key = get_api_key()
            if not api_key:
                st.error("Gemini API key is missing. Configure GEMINI_API_KEY first.")
            else:
                task = (
                    f"Explain anomaly type '{issue_type}' for entity '{entity_id}'. "
                    f"Rule-based detector description: {description}. "
                    f"Reviewer question: {reviewer_context or 'Explain the finding and suggest a review action.'}"
                )
                with st.spinner("Gemini is analyzing the supplied evidence..."):
                    try:
                        st.markdown(explain_with_gemini(api_key, task, evidence))
                    except Exception as exc:
                        st.error("Gemini request failed.")
                        st.code("{}: {}".format(type(exc).__name__, str(exc)))

with tab_ask:
    st.subheader("Ask questions about this dataset")
    st.write(
        "Ask about the available summary and detected findings. The app does not let the model execute arbitrary SQL."
    )
    question = st.text_area(
        "Your question",
        placeholder="Which anomaly types were detected, and what should a reviewer prioritize?",
        key="general_question",
    )
    if st.button("Ask Gemini", type="primary", key="ask_gemini"):
        api_key = get_api_key()
        if not question.strip():
            st.warning("Enter a question first.")
        elif not api_key:
            st.error("Gemini API key is missing. Configure GEMINI_API_KEY first.")
        else:
            context = {
                "metrics": metrics,
                "detected_findings": [
                    {"issue_type": t, "entity_id": entity, "description": desc}
                    for t, entity, desc in findings
                ],
                "dataset_summary": dataset_summary,
            }
            with st.spinner("Preparing an evidence-grounded answer..."):
                try:
                    st.markdown(explain_with_gemini(api_key, question, context))
                except Exception as exc:
                    st.error("Gemini request failed. Check your API key, model access, and network connection.")
                    st.caption(str(exc))

st.divider()
st.caption(
    "AI-generated explanations are advisory. Verify findings against database evidence and business rules before taking action."
)
