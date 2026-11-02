import streamlit as st

from frontend.common import (
    call, get_latest_resume, nav, page_header, pills, require_login, select_job, soft,
)

require_login()
first_name = (st.session_state.get("user_name") or "").split(" ")[0] or "there"
page_header(f"Welcome back, {first_name}", "Your personalised career overview")

resume = get_latest_resume()
if resume is None:
    recs = []
else:
    # UC011: prefer the user's stored (unfiltered) recommendations; only recompute live if
    # nothing has been stored yet (e.g. first visit) -- that live call then gets stored too.
    recs = call("GET", "/recommendations/latest")
    if not recs:
        recs = call("POST", "/recommendations", json={"resume_id": resume["id"], "k": 2})
    recs = recs[:2]

col_rec, col_skill, col_perf = st.columns(3, gap="medium")

with col_rec:
    with st.container(border=True):
        st.subheader("Top Recommendations")
        if resume is None:
            st.caption("Upload a resume to see job matches.")
            if st.button("Upload resume", type="primary", key="dash_upload"):
                nav("resume")
        elif not recs:
            st.caption("No matches found yet.")
        else:
            for r in recs:
                st.markdown(f"**{r['title']}**  \n{r['company']}")
                st.markdown(
                    f'<span class="g2k-pill g2k-match">{r["match_pct"]}% Match</span>',
                    unsafe_allow_html=True,
                )
        if recs and st.button("View all recommended jobs", key="dash_all_recs"):
            st.session_state["pending_find_tab"] = "AI Recommended"
            nav("find_job")

with col_skill:
    with st.container(border=True):
        st.subheader("Skill Match Summary")
        # UC011 step 4: prefer the latest stored skill match; only compute live (for the top
        # recommendation) if nothing has been checked yet -- that live call then gets stored too.
        gap, err = soft("GET", "/skill-gap/latest")
        if not gap and recs:
            # explain=False: this card never shows the explanation, so skip paying for the LLM call.
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
                st.progress(gap["match_pct"] / 100, text=f"Skill match: {gap['match_pct']:.0f}%")
                st.caption("Top missing skills")
                pills(gap["missing"][:4], "missing")
            if st.button("View Details →", key="dash_skill_details"):
                select_job(gap["job_id"], "skill_match")

with col_perf:
    with st.container(border=True):
        st.subheader("Interview Performance")
        sessions, err = soft("GET", "/interviews")
        completed = [s for s in (sessions or []) if s["overall_score"] is not None]
        if completed:
            latest = completed[0]
            st.caption(f"Latest: {latest['job_title']} · {latest['company']}")
            st.markdown(
                f'<div class="g2k-score">{latest["overall_score"]}<span> / 100</span></div>',
                unsafe_allow_html=True,
            )
        elif err:
            st.caption(err)
        else:
            st.caption("Complete a mock interview to see your score.")
        if st.button("View interview history", key="dash_history"):
            nav("interview_history")

st.write("")
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
