import html

import streamlit as st

from frontend.common import (
    call, donut, get_latest_resume, nav, page_header, pills, require_login, start_interview,
    upload_prompt,
)


def _checklist(items: list[str], matched: bool) -> None:
    if not items:
        st.caption("None")
        return
    mark, color = ("✓", "#166534") if matched else ("✗", "#92400E")
    rows = "".join(
        '<div style="display:flex; align-items:center; gap:0.5rem; padding:3px 0;">'
        f'<span style="color:{color}; font-weight:700;">{mark}</span>'
        f'<span>{html.escape(item.title())}</span></div>'
        for item in items
    )
    st.markdown(rows, unsafe_allow_html=True)

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
    st.subheader("Skill Match", help="Skill Match counts the skills listed on this job posting "
                 "only -- it's not a semantic read of the full description (that's the AI Match "
                 "% shown on Job Details).")
    if gap["match_pct"] is None:
        st.info(gap["message"])
    else:
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            st.plotly_chart(donut(gap["match_pct"], "Skill Match"), use_container_width=True,
                            config={"displayModeBar": False})
        total = len(gap["matched"]) + len(gap["missing"])
        if total:
            st.caption(f"You match {len(gap['matched'])} out of {total} required skills for this role.")
        if gap["message"]:
            st.info(gap["message"])
            # UC008 alt flow 3.1: no skills on the resume -- point the user at fixing that, not
            # just the skill/missing lists below, which would all be empty/unhelpful here.
            if not resume["skills"] and st.button("Go to Resume Upload", type="primary", key="sm_upload",
                                                   icon=":material/upload_file:"):
                nav("resume")

c1, c2 = st.columns(2, gap="medium")
with c1:
    with st.container(border=True):
        st.subheader("Matched skills")
        _checklist(gap["matched"], matched=True)
with c2:
    with st.container(border=True):
        st.subheader("Missing skills")
        _checklist(gap["missing"], matched=False)

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
