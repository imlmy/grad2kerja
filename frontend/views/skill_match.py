import html

import streamlit as st

from frontend.common import (
    call, donut, get_latest_resume, nav, page_header, require_login, start_interview,
    upload_prompt,
)


def _checklist(items: list[str], matched: bool) -> None:
    if not items:
        st.caption("None yet")
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
        st.caption("None yet")
        return
    if software:
        st.caption("Software & tools")
        _checklist(software, matched)
    if technical:
        st.caption("Technical skills")
        _checklist(technical, matched)


def _language_pills(matched: list[str], missing: list[str]) -> str:
    """Matched languages as a green pill with a check mark, missing ones as a plain amber
    pill -- languages are informational only, never scored like skills."""
    parts = [
        '<span class="g2k-pill g2k-match"><span style="font-weight:700;">✓ </span>'
        f'{html.escape(lang.title())}</span>'
        for lang in matched
    ]
    parts += [f'<span class="g2k-pill g2k-missing">{html.escape(lang.title())}</span>' for lang in missing]
    return " ".join(parts)


def _spacer() -> None:
    st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)


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

page_header("Skill Match Analysis", f"{job['title']} at {job['company']}")

# Summary: donut + match count, compact.
with st.container(border=True):
    if gap["match_pct"] is None:
        st.info(gap["message"])
        # UC008 alt flow 3.1: no skills on the resume -- point the user at fixing that, not
        # just the skill/missing lists below, which would all be empty/unhelpful here.
        if not resume["skills"] and st.button("Go to Resume Upload", type="primary", key="sm_upload",
                                               icon=":material/upload_file:"):
            nav("resume")
    else:
        d_col, s_col = st.columns([1, 2], gap="medium", vertical_alignment="center")
        with d_col:
            st.plotly_chart(donut(gap["match_pct"], "Skill Match", height=160), use_container_width=True,
                            config={"displayModeBar": False})
        with s_col:
            total = len(gap["matched"]) + len(gap["missing"])
            if total:
                st.markdown(f"**{len(gap['matched'])} of {total} required skills matched**")
            st.caption("Based on software and technical skills. Soft skills are shown separately "
                       "because resumes often show them through experience rather than listing them.")

_spacer()

with st.container(border=True):
    st.subheader("Skills")
    sk1, sk2 = st.columns(2, gap="medium")
    with sk1:
        st.markdown('<span style="color:#166534; font-weight:600;">✓ Matched</span>', unsafe_allow_html=True)
        _grouped_checklist(gap.get("matched_by_type"), matched=True)
    with sk2:
        st.markdown('<span style="color:#92400E; font-weight:600;">✗ Missing</span>', unsafe_allow_html=True)
        _grouped_checklist(gap.get("missing_by_type"), matched=False)

_spacer()

has_soft = bool(gap.get("soft_skills_required"))
has_languages = bool(gap["matched_languages"] or gap["missing_languages"])
if has_soft or has_languages:
    soft_col, lang_col = st.columns(2, gap="medium")
    with soft_col:
        if has_soft:
            with st.container(border=True, height="stretch"):
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
    with lang_col:
        if has_languages:
            with st.container(border=True, height="stretch"):
                st.subheader("Languages")
                st.markdown(_language_pills(gap["matched_languages"], gap["missing_languages"]),
                            unsafe_allow_html=True)
                st.caption("Languages are shown separately and don't affect the score.")
    _spacer()

if gap.get("explanation"):
    with st.container(border=True):
        st.subheader("Why this matters")
        st.write(gap["explanation"])
    _spacer()
elif gap.get("explanation_note"):
    # UC008 alt flow 8.1: the skill match itself is still shown above; only the explanation failed.
    st.warning(gap["explanation_note"])
    _spacer()

if st.button("Practise interview for this role", type="primary", key="sm_interview"):
    start_interview(jid)
