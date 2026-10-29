"""Staff / reviewer view: the original anomaly dashboard, kept as a separate mode."""
import pandas as pd
import streamlit as st

from src import ai_helper
from src.app_queries import get_anomaly_evidence, get_anomaly_findings, get_dashboard_metrics, get_dataset_summary

SYSTEM = (
    "You are YottaFlex AI, an assistant for reviewing assignment-management data quality. Treat the supplied database evidence as the "
    "only source of facts. Do not invent values, policies, causes or events. Distinguish observed evidence from recommendations. "
    "Do not change grades or claim any action has been taken. Use headings: Finding, Evidence, Business impact, Recommended reviewer action."
)


def _ask(task, evidence):
    try:
        text, model = ai_helper.generate(SYSTEM, f"Task:\n{task}\n\nEvidence (JSON):\n{evidence}")
        st.markdown(text)
        st.caption(f"Model: {model}. Advisory only; verify against the database.")
    except ai_helper.AIUnavailable as exc:
        st.warning(f"AI explanation unavailable: {exc}")


def render():
    metrics, findings, summary = get_dashboard_metrics(), get_anomaly_findings(), get_dataset_summary()
    tab_a, tab_b, tab_c = st.tabs(["📊 Overview", "🔎 Anomaly Investigator", "💬 Ask about the data"])
    with tab_a:
        cols = st.columns(6)
        for col, key in zip(cols, ["courses", "learners", "assignments", "submissions", "grades", "appeals"]):
            col.metric(key.title(), f"{metrics.get(key, 0):,}")
        st.markdown("#### Detected data-quality findings")
        if findings:
            st.dataframe(pd.DataFrame(findings, columns=["Issue type", "Entity ID", "Rule-based description"]),
                         use_container_width=True, hide_index=True)
        else:
            st.success("No anomalies detected by the current rules.")
        st.info("Python and SQL detect anomalies; the AI only explains evidence. Records are synthetic test data.")
    with tab_b:
        if not findings:
            st.success("No anomalies to investigate.")
        else:
            opts = [f"{t} · {e}" for t, e, _ in findings]
            sel = st.selectbox("Select a finding", opts)
            issue, entity, desc = findings[opts.index(sel)]
            evidence = get_anomaly_evidence(issue, entity)
            st.write(desc)
            with st.expander("View source evidence"):
                st.json(evidence)
            qn = st.text_area("Optional question", key="inv_q")
            if st.button("✨ Explain this finding", type="primary"):
                with st.spinner("Analyzing evidence…"):
                    _ask(f"Explain anomaly '{issue}' for entity '{entity}'. Detector: {desc}. Question: {qn or 'Explain and suggest a review action.'}", evidence)
    with tab_c:
        q = st.text_area("Your question", key="gen_q", placeholder="Which anomaly types were detected and what should we prioritise?")
        if st.button("Ask", type="primary") and q.strip():
            ctx = dict(metrics=metrics, findings=[dict(issue_type=t, entity_id=e, description=d) for t, e, d in findings], summary=summary)
            with st.spinner("Preparing answer…"):
                _ask(q, ctx)
