import html

import plotly.graph_objects as go
import streamlit as st

from frontend.common import (
    call, format_date, nav, overall_label, require_login, score_tier, start_interview, tier_hex,
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


def _spacer() -> None:
    st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)


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


job_title = report["job_title"] or "Mock interview"
st.markdown(
    f'<div style="font-size:2rem; font-weight:700; line-height:1.25;">{html.escape(job_title)}</div>',
    unsafe_allow_html=True,
)
if report.get("company"):
    st.markdown(f'<div style="color:#64748B;">{html.escape(report["company"])}</div>', unsafe_allow_html=True)

date_str = format_date(report["created_at"])
if date_str:
    st.markdown(
        f'<div style="color:#64748B; font-size:0.85rem; margin-top:0.4rem;">{html.escape(date_str)}</div>',
        unsafe_allow_html=True,
    )

_spacer()

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

    right_fields = [("QUESTIONS ANSWERED", f"{len(answered_qs)} of {len(report['questions'])}")]
    if len(type_avgs) >= 2:
        best_type = max(type_avgs, key=type_avgs.get)
        worst_type = min(type_avgs, key=type_avgs.get)
        if type_avgs[best_type] == type_avgs[worst_type]:
            right_fields.append(("STRONGEST AREA", "All areas scored equally"))
            right_fields.append(("NEEDS MOST WORK", "All areas scored equally"))
        else:
            right_fields.append(("STRONGEST AREA", f"{best_type.capitalize()} · {type_avgs[best_type]:.1f}/10"))
            right_fields.append(("NEEDS MOST WORK", f"{worst_type.capitalize()} · {type_avgs[worst_type]:.1f}/10"))

    right_cells = "".join(
        f'<div style="flex:1; padding:0 1.25rem;{" border-left:1px solid #E5E7EB;" if i else ""}">'
        f'<div class="g2k-caption">{html.escape(label)}</div>'
        f'<div style="font-weight:700; margin-top:0.25rem;">{html.escape(value)}</div></div>'
        for i, (label, value) in enumerate(right_fields)
    )

    st.info(
        "Scores and feedback are AI-generated guidance to help you improve. They are not a "
        "prediction of your interview outcome."
    )
    with st.container(border=True):
        st.markdown(
            '<div style="display:flex; align-items:center; flex-wrap:wrap; gap:1.5rem;">'
            '<div style="flex:0 0 40%; min-width:180px;">'
            '<div class="g2k-caption">OVERALL SCORE</div>'
            f'<div class="g2k-score g2k-text-{tier}">{report["overall_score"]}<span> / 100</span></div>'
            f'<span class="g2k-pill g2k-tier-{tier}">{html.escape(overall_label(report["overall_score"]))}</span>'
            '</div>'
            f'<div style="flex:1; display:flex; min-width:220px;">{right_cells}</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    _spacer()

    st.subheader("Score by question")
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
        height=240, margin=dict(l=0, r=0, t=20, b=0), bargap=0.55,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(range=[0, 10], title=None, dtick=2, gridcolor="#F1F5F9", showline=False,
                   zeroline=False, tickfont=dict(size=12, color="#64748B")),
        xaxis=dict(title=None, showline=False, tickfont=dict(size=12, color="#64748B")),
    )
    st.plotly_chart(bars, use_container_width=True, config={"displayModeBar": False})

    _spacer()

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

_spacer()

c1, c2 = st.columns(2)
if c1.button("Practise again", type="primary", key="fr_again"):
    start_interview(report["job_id"])
if c2.button("Back to interview history", key="fr_history"):
    nav("interview_history")
