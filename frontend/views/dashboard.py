import plotly.graph_objects as go
import streamlit as st

from frontend.common import (
    call, company_avatar, donut, format_date, get_latest_resume, match_badge, nav, page_header,
    pills, require_login, select_job, soft, stat_tile,
)

require_login()
first_name = (st.session_state.get("user_name") or "").split(" ")[0] or "there"
page_header(f"Welcome back, {first_name}", "Your personalised career overview")

resume = get_latest_resume()
if resume is None:
    recs = []
    all_recs = []
else:
    all_recs = call("GET", "/recommendations/latest")
    if not all_recs:
        all_recs = call("POST", "/recommendations", json={"resume_id": resume["id"], "k": 2})
    recs = all_recs[:2]

saved_jobs, _ = soft("GET", "/saved-jobs")
all_interviews, _ = soft("GET", "/interviews")
completed_sessions = [s for s in (all_interviews or []) if s["overall_score"] is not None]
avg_interview_score = (
    round(sum(s["overall_score"] for s in completed_sessions) / len(completed_sessions))
    if completed_sessions else None
)

t1, t2, t3, t4 = st.columns(4, gap="medium")
with t1:
    stat_tile("Jobs Matched", str(len(all_recs)), "work")
with t2:
    stat_tile("Saved Jobs", str(len(saved_jobs or [])), "bookmark")
with t3:
    stat_tile("Interviews Completed", str(len(completed_sessions)), "mic")
with t4:
    stat_tile("Avg Interview Score", f"{avg_interview_score}/100" if avg_interview_score is not None else "—",
              "trending_up")

st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)
col_rec, col_skill, col_perf = st.columns(3, gap="medium")

with col_rec:
    with st.container(border=True, height="stretch"):
        st.subheader("Top Recommendations")
        if resume is None:
            st.caption("Upload a resume to see job matches.")
            if st.button("Upload resume", type="primary", key="dash_upload"):
                nav("resume")
        elif not recs:
            st.caption("No matches found yet.")
        else:
            for r in recs:
                a1, a2 = st.columns([1, 6], vertical_alignment="center")
                with a1:
                    st.markdown(company_avatar(r["company"]), unsafe_allow_html=True)
                with a2:
                    st.markdown(f"**{r['title']}**  \n{r['company']}")
                st.markdown(match_badge(r["match_pct"], "ai"), unsafe_allow_html=True)
        if recs and st.button("View all recommended jobs", key="dash_all_recs"):
            st.session_state["pending_find_tab"] = "AI Recommended"
            nav("find_job")

with col_skill:
    with st.container(border=True, height="stretch"):
        st.subheader("Skill Match Summary")
        gap, err = soft("GET", "/skill-gap/latest")
        if not gap and recs:
            gap, err = soft("POST", "/skill-gap",
                            json={"resume_id": resume["id"], "job_id": recs[0]["job_id"], "explain": False})
        if not gap:
            st.caption(err or "Available once you have a resume and a matched job.")
        else:
            if gap.get("title"):
                st.caption(f"For {gap['title']}")
            if gap["match_pct"] is None:
                st.caption("No specific skills listed for this job.")
            else:
                st.plotly_chart(donut(gap["match_pct"], "Skill Match"), use_container_width=True,
                                config={"displayModeBar": False})
                st.caption("Top missing skills")
                pills(gap["missing"][:4], "missing")
            if st.button("View Details →", key="dash_skill_details"):
                select_job(gap["job_id"], "skill_match")

with col_perf:
    with st.container(border=True, height="stretch"):
        st.subheader("Interview Performance")
        if completed_sessions:
            latest = completed_sessions[0]
            st.caption(f"Latest: {latest['job_title']} · {latest['company']}")
            st.markdown(
                f'<div class="g2k-score">{latest["overall_score"]}<span> / 100</span></div>',
                unsafe_allow_html=True,
            )
            if len(completed_sessions) >= 2:
                oldest_first = list(reversed(completed_sessions))
                trend = go.Figure(data=[go.Scatter(
                    x=[format_date(s["created_at"]) for s in oldest_first],
                    y=[s["overall_score"] for s in oldest_first],
                    mode="lines+markers", line=dict(color="#0B3FB8"), marker=dict(color="#0B3FB8"),
                )])
                trend.update_layout(
                    height=160, margin=dict(l=0, r=0, t=10, b=0),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    yaxis=dict(range=[0, 100], title=None), xaxis=dict(title=None),
                )
                st.plotly_chart(trend, use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("Complete a mock interview to see your score.")
        if st.button("View interview history", key="dash_history"):
            nav("interview_history")

st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)
with st.container(key="g2k_refine_profile"):
    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    with c1:
        st.subheader("Refine your profile")
        if resume is None:
            st.write("Upload your latest resume to get personalised job matches and a deeper "
                      "skill gap analysis.")
        else:
            st.write("Update your resume to keep your job matches and skill gap analysis accurate.")
    with c2:
        label = "Upload Resume" if resume is None else "Update your resume"
        if st.button(label, type="primary", key="dash_refine_resume"):
            nav("resume")
