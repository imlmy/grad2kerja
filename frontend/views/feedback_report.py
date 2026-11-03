import plotly.graph_objects as go
import streamlit as st

from frontend.common import (
    call, format_date, nav, overall_label, page_header, require_login, score_tier, start_interview,
    tier_hex, type_tag,
)

require_login()
sid = st.session_state.get("report_session_id")
if sid is None:
    st.info("Finish a mock interview to see its report.")
    if st.button("Go to Interview History", key="fr_empty"):
        nav("interview_history")
    st.stop()

report = call("GET", f"/interviews/{sid}")


def _truncate(text: str, limit: int = 80) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_space = cut.rfind(" ")
    if last_space > 0:
        cut = cut[:last_space]
    return cut.rstrip() + "…"


def _resume_interview() -> None:
    """Rebuild the session state interview.py expects from this report, so an unfinished
    interview can be continued instead of started over."""
    st.session_state["interview"] = {
        "id": report["id"], "job_id": report["job_id"], "job_title": report["job_title"],
        "company": report["company"], "personalised": report.get("personalised"),
        "questions": report["questions"],
    }
    st.session_state["interview_answers"] = {
        q["id"]: {"answer": q["answer"]["text"], "score": q["answer"]["score"],
                  "strengths": q["answer"]["strengths"], "improvements": q["answer"]["improvements"]}
        for q in report["questions"] if q["answer"]
    }
    first_unanswered = next(
        (i for i, q in enumerate(report["questions"]) if not q["answer"]), len(report["questions"]),
    )
    st.session_state["q_index"] = first_unanswered
    nav("interview")


title = report["job_title"] or "Mock interview"
if report.get("company"):
    title += f" — {report['company']}"

page_header(title, format_date(report["created_at"]))
pills_html = '<span class="g2k-pill g2k-neutral">AI Practice Session</span>'
if report.get("personalised"):
    pills_html += ' <span class="g2k-pill g2k-neutral">Personalised</span>'
st.markdown(pills_html, unsafe_allow_html=True)

answered_qs = [q for q in report["questions"] if q["answer"]]

if report["overall_score"] is None:
    st.markdown(
        '<div class="g2k-empty-state"><span class="material-symbols-outlined">quiz</span>'
        "<div>No answers recorded yet</div></div>",
        unsafe_allow_html=True,
    )
    _, mid, _ = st.columns([2, 1, 2])
    with mid:
        if st.button("Continue interview", type="primary", key="fr_continue"):
            _resume_interview()
else:
    tier = score_tier(report["overall_score"])
    with st.container(border=True):
        s1, s2, s3, s4 = st.columns(4, gap="medium")
        with s1:
            st.markdown(
                f'<div class="g2k-score g2k-text-{tier}">{report["overall_score"]}'
                '<span> / 100</span></div>',
                unsafe_allow_html=True,
            )
        with s2:
            st.write(overall_label(report["overall_score"]))
        with s3:
            st.write(f"{len(answered_qs)} of {len(report['questions'])} questions answered")
        with s4:
            st.caption("Scores and feedback are AI-generated guidance to help you improve, "
                       "not a prediction of your interview outcome.")

    by_type: dict[str, list[float]] = {}
    for q in answered_qs:
        if q.get("type"):
            by_type.setdefault(q["type"].lower(), []).append(q["answer"]["score"])
    if by_type:
        st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
        st.caption("Average by question type")
        type_cols = st.columns(len(by_type), gap="medium")
        for col, (qtype, scores) in zip(type_cols, by_type.items()):
            avg = sum(scores) / len(scores)
            avg_tier = score_tier(avg * 10)
            with col:
                with st.container(border=True):
                    st.markdown(type_tag(qtype), unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="g2k-score g2k-text-{avg_tier}" style="font-size:1.8rem;">'
                        f'{avg:.1f}<span> / 10</span></div>',
                        unsafe_allow_html=True,
                    )

    with st.container(border=True):
        st.subheader("Score by Question")
        bars = go.Figure(data=[go.Bar(
            x=[f"Q{q['position']}" for q in answered_qs],
            y=[q["answer"]["score"] for q in answered_qs],
            marker=dict(color=[tier_hex(q["answer"]["score"] * 10) for q in answered_qs]),
        )])
        bars.update_layout(
            height=260, margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(range=[0, 10], title=None), xaxis=dict(title=None),
        )
        st.plotly_chart(bars, use_container_width=True, config={"displayModeBar": False})

st.subheader("Question review")
for q in report["questions"]:
    answer = q["answer"]
    score_part = f"{answer['score']}/10" if answer else "not answered"
    title = f"Question {q['position']} — {score_part} · {_truncate(q['question'])}"
    with st.expander(title, expanded=q["position"] == 1):
        if q.get("type"):
            st.markdown(type_tag(q["type"]), unsafe_allow_html=True)
        st.markdown(f"**{q['question']}**")
        if answer:
            st.caption("Your answer")
            st.write(answer["text"])
            st.caption("AI feedback")
            st.write(f"**Done well:** {answer['strengths']}")
            st.write(f"**To improve:** {answer['improvements']}")

c1, c2 = st.columns(2)
if c1.button("Practise again", type="primary", key="fr_again"):
    start_interview(report["job_id"])
if c2.button("Back to interview history", key="fr_history"):
    nav("interview_history")
