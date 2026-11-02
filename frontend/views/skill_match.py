import streamlit as st

from frontend.common import (
    call, get_latest_resume, nav, page_header, pills, require_login, start_interview, upload_prompt,
)

require_login()
jid = st.session_state.get("selected_job_id")
if jid is None:
    st.info("Pick a job from Find a Job first.")
    if st.button("Back to jobs", key="sm_back_empty"):
        nav("find_job")
    st.stop()

resume = get_latest_resume()
if resume is None:
    upload_prompt("Upload your resume to see how your skills compare with this role.")

job = call("GET", f"/jobs/{jid}")
# UC008 step 8: explain=True (the default) generates the AI explanation as part of this same
# call, so there's no separate button/click for it.
with st.spinner("Checking your skill match..."):
    gap = call("POST", "/skill-gap", json={"resume_id": resume["id"], "job_id": jid})

if st.button("← Back to job", key="sm_back"):
    nav("job_details")

page_header("Skill Match Analysis", job["title"])

with st.container(border=True):
    if gap["match_pct"] is None:
        st.info(gap["message"])
    else:
        st.markdown(
            f'<div class="g2k-score">{gap["match_pct"]:.0f}%<span> skill match</span></div>',
            unsafe_allow_html=True,
        )
        st.progress(gap["match_pct"] / 100)
        total = len(gap["matched"]) + len(gap["missing"])
        if total:
            st.caption(f"You match {len(gap['matched'])} out of {total} required skills for this role.")
        if gap["message"]:
            st.info(gap["message"])
            # UC008 alt flow 3.1: no skills on the resume -- point the user at fixing that, not
            # just the skill/missing lists below, which would all be empty/unhelpful here.
            if not resume["skills"] and st.button("Go to Resume Upload", type="primary", key="sm_upload"):
                nav("resume")

c1, c2 = st.columns(2, gap="medium")
with c1:
    with st.container(border=True):
        st.subheader("Matched skills")
        pills(gap["matched"], "match")
with c2:
    with st.container(border=True):
        st.subheader("Missing skills")
        pills(gap["missing"], "missing")

if gap["matched_languages"] or gap["missing_languages"]:
    l1, l2 = st.columns(2, gap="medium")
    with l1:
        with st.container(border=True):
            st.subheader("Matched languages")
            pills(gap["matched_languages"], "match")
    with l2:
        with st.container(border=True):
            st.subheader("Missing languages")
            pills(gap["missing_languages"], "missing")

if gap.get("explanation"):
    with st.container(border=True):
        st.caption("AI explanation")
        st.write(gap["explanation"])
elif gap.get("explanation_note"):
    # UC008 alt flow 8.1: the skill match itself is still shown above; only the explanation failed.
    st.warning(gap["explanation_note"])

if st.button("Practise interview for this role", type="primary", key="sm_interview"):
    start_interview(jid)
