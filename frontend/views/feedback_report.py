import plotly.graph_objects as go
import streamlit as st

from frontend.common import (
    call, format_date, nav, overall_label, page_header, require_login, start_interview, tier_hex,
    type_tag,
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


title = report["job_title"] or "Mock interview"
if report.get("company"):
    title += f" — {report['company']}"

left, right = st.columns([3, 1], gap="large")
with left:
    page_header(title, format_date(report["created_at"]))
    pills_html = '<span class="g2k-pill g2k-neutral">AI Practice Session</span>'
    if report.get("personalised"):
        pills_html += ' <span class="g2k-pill g2k-neutral">Personalised</span>'
    st.markdown(pills_html, unsafe_allow_html=True)
with right:
    with st.container(border=True):
        if report["overall_score"] is None:
            st.write("No answers have been recorded for this interview yet.")
        else:
            st.markdown(
                f'<div class="g2k-score">{report["overall_score"]}<span> / 100</span></div>',
                unsafe_allow_html=True,
            )
            st.caption("Scores and feedback are AI-generated guidance to help you improve, "
                       "not a prediction of your interview outcome.")
            answered_count = sum(1 for q in report["questions"] if q["answer"])
            st.caption(f"Average score across {answered_count} answered question(s)")
            st.write(overall_label(report["overall_score"]))

answered_qs = [q for q in report["questions"] if q["answer"]]
if answered_qs:
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
