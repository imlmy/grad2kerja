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
    st.markdown(f'<div style="padding-bottom:0.75rem;">{rows}</div>', unsafe_allow_html=True)


def _grouped_checklist(by_type: dict | None, matched: bool) -> None:
    """Like _checklist, but split under "Software & tools" / "Technical skills" subheadings
    (an empty group is omitted rather than shown with nothing under it)."""
    by_type = by_type or {}
    software = by_type.get("software") or []
    technical = by_type.get("technical") or []
    if not software and not technical:
        st.caption("None")
        return
    if software:
        st.caption("Software & tools")
        _checklist(software, matched)
    if technical:
        st.caption("Technical skills")
        _checklist(technical, matched)

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

if st.button("Back to job", key="sm_back", icon=":material/arrow_back:"):
    nav("job_details")

page_header("Skill Match Analysis", job["title"])

with st.container(border=True):
    st.subheader("Skill Match", help="Based on software and technical skills. Soft skills are "
                 "shown separately because resumes often show them through experience rather "
                 "than listing them.")
    if gap["match_pct"] is None:
        st.info(gap["message"])
    else:
        d_col, s_col = st.columns([1, 2], gap="medium", vertical_alignment="center")
        with d_col:
            st.plotly_chart(donut(gap["match_pct"], "Skill Match"), use_container_width=True,
                            config={"displayModeBar": False})
        with s_col:
            total = len(gap["matched"]) + len(gap["missing"])
            if total:
                st.write(f"**{len(gap['matched'])} of {total} required skills matched**")
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
        _grouped_checklist(gap.get("matched_by_type"), matched=True)
with c2:
    with st.container(border=True):
        st.subheader("Missing skills")
        _grouped_checklist(gap.get("missing_by_type"), matched=False)

if gap.get("soft_skills_required"):
    with st.container(border=True):
        st.subheader("Soft skills this role values")
        listed = set(gap.get("soft_skills_listed") or [])
        pills_html = " ".join(
            '<span class="g2k-pill g2k-neutral">'
            + ('<span style="color:#166534; font-weight:700;">✓ </span>' if s in listed else "")
            + f'{html.escape(s.title())}</span>'
            for s in gap["soft_skills_required"]
        )
        st.markdown(pills_html, unsafe_allow_html=True)
        st.caption("Soft skills are usually shown through your experience rather than listed. "
                   "Practise them in a mock interview.")
        if st.button("Practise interview", key="sm_soft_interview", icon=":material/mic:"):
            start_interview(jid)

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
