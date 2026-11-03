import html

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
                  "strengths": q["answer"]["strengths"], "improvements": q["answer"]["improvements"],
                  "improved_answer": q["answer"].get("improved_answer")}
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
    by_type: dict[str, list[float]] = {}
    for q in answered_qs:
        if q.get("type"):
            by_type.setdefault(q["type"].lower(), []).append(q["answer"]["score"])
    type_avgs = {t: sum(scores) / len(scores) for t, scores in by_type.items()}

    with st.container(border=True):
        left, right = st.columns([2, 3], gap="large", vertical_alignment="center")
        with left:
            st.caption("OVERALL SCORE")
            st.markdown(
                f'<div class="g2k-score g2k-text-{tier}">{report["overall_score"]}'
                '<span> / 100</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<span class="g2k-pill g2k-tier-{tier}">'
                f'{html.escape(overall_label(report["overall_score"]))}</span>',
                unsafe_allow_html=True,
            )
            st.progress(report["overall_score"] / 100)
        with right:
            if len(type_avgs) >= 2:
                r1, r2, r3 = st.columns(3, gap="medium")
            else:
                (r1,) = st.columns(1)
            with r1:
                st.caption("QUESTIONS ANSWERED")
                st.markdown(f"**{len(answered_qs)} of {len(report['questions'])}**")
            if len(type_avgs) >= 2:
                best_type = max(type_avgs, key=type_avgs.get)
                worst_type = min(type_avgs, key=type_avgs.get)
                with r2:
                    st.caption("STRONGEST AREA")
                    st.markdown(f"**{best_type.capitalize()} · {type_avgs[best_type]:.1f}/10**")
                with r3:
                    st.caption("NEEDS MOST WORK")
                    st.markdown(f"**{worst_type.capitalize()} · {type_avgs[worst_type]:.1f}/10**")
    st.caption("ℹ️ Scores and feedback are AI-generated guidance to help you improve, not a "
               "prediction of your interview outcome.")

    if type_avgs:
        st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
        st.caption("Average by question type")
        type_cols = st.columns(len(type_avgs), gap="medium")
        for col, (qtype, avg) in zip(type_cols, type_avgs.items()):
            avg_tier = score_tier(avg * 10)
            with col:
                with st.container(border=True, height="stretch"):
                    st.markdown(type_tag(qtype), unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="g2k-score g2k-text-{avg_tier}" style="font-size:1.8rem;">'
                        f'{avg:.1f}<span> / 10</span></div>',
                        unsafe_allow_html=True,
                    )
                    n = len(by_type[qtype])
                    st.caption(f"{n} question{'s' if n != 1 else ''}")

    with st.container(border=True):
        st.subheader("Score by Question")
        x_labels = [
            f"Q{q['position']} · {q['type'].capitalize()}" if q.get("type") else f"Q{q['position']}"
            for q in answered_qs
        ]
        scores = [q["answer"]["score"] for q in answered_qs]
        bars = go.Figure(data=[go.Bar(
            x=x_labels, y=scores,
            text=[str(s) for s in scores], textposition="outside",
            marker=dict(color=[tier_hex(s * 10) for s in scores]),
        )])
        bars.update_layout(
            height=260, margin=dict(l=0, r=0, t=20, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(range=[0, 10], title=None, dtick=2), xaxis=dict(title=None),
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
            if answer.get("improved_answer"):
                with st.expander("See an improved version of your answer", icon=":material/auto_awesome:"):
                    st.caption("AI-suggested rewrite of your answer. Fill in the [bracketed] parts "
                               "with your own real experience.")
                    st.write(answer["improved_answer"])

c1, c2 = st.columns(2)
if c1.button("Practise again", type="primary", key="fr_again"):
    start_interview(report["job_id"])
if c2.button("Back to interview history", key="fr_history"):
    nav("interview_history")
