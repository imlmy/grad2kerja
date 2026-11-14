import html

import streamlit as st

from frontend.common import (
    call, display_skill, donut, get_latest_resume, nav, page_header, pills, require_login,
    start_interview, upload_prompt,
)


def _skill_group(by_type: dict | None, kind: str) -> None:
    """Pills for the Matched/Missing skills row. "Software & tools"/"Technical skills"
    subheadings are shown only when BOTH groups are non-empty; otherwise the pills run
    together with no label."""
    by_type = by_type or {}
    software = by_type.get("software") or []
    technical = by_type.get("technical") or []
    if not software and not technical:
        st.caption("None yet")
        return
    if software and technical:
        st.caption("Software & tools")
        pills(software, kind)
        st.caption("Technical skills")
        pills(technical, kind)
    else:
        pills(software + technical, kind)


def _language_pills(matched: list[str], missing: list[str]) -> str:
    """Matched languages as a green pill with a check mark, missing ones as a plain amber
    pill -- languages are informational only, never scored like skills."""
    parts = [
        '<span class="g2k-pill g2k-match"><span style="font-weight:700;">✓ </span>'
        f'{html.escape(display_skill(lang))}</span>'
        for lang in matched
    ]
    parts += [f'<span class="g2k-pill g2k-missing">{html.escape(display_skill(lang))}</span>' for lang in missing]
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

# Summary: donut + match count, compact, with the text close to the donut.
with st.container(border=True):
    if gap["match_pct"] is None:
        st.info(gap["message"])
        # UC008 alt flow 3.1: no skills on the resume -- point the user at fixing that, not
        # just the skill/missing lists below, which would all be empty/unhelpful here.
        if not resume["skills"] and st.button("Go to Resume Upload", type="primary", key="sm_upload",
                                               icon=":material/upload_file:"):
            nav("resume")
    else:
        d_col, s_col = st.columns([2, 3], gap="small", vertical_alignment="center")
        with d_col:
            st.plotly_chart(donut(gap["match_pct"], "Skill Match", height=150), use_container_width=True,
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
        _skill_group(gap.get("matched_by_type"), "match")
    with sk2:
        st.markdown('<span style="color:#92400E; font-weight:600;">✗ Missing</span>', unsafe_allow_html=True)
        _skill_group(gap.get("missing_by_type"), "missing")

_spacer()

has_soft = bool(gap.get("soft_skills_required"))
has_languages = bool(gap["matched_languages"] or gap["missing_languages"])
if has_soft or has_languages:
    with st.container(border=True):
        st.subheader("Not counted in your score")
        if has_soft:
            st.caption("Soft skills")
            listed = set(gap.get("soft_skills_listed") or [])
            soft_pills = " ".join(
                '<span class="g2k-pill g2k-neutral">'
                + ('<span style="color:#166534; font-weight:700;">✓ </span>' if s in listed else "")
                + f'{html.escape(display_skill(s))}</span>'
                for s in gap["soft_skills_required"]
            )
            st.markdown(soft_pills, unsafe_allow_html=True)
        if has_languages:
            st.caption("Languages")
            st.markdown(_language_pills(gap["matched_languages"], gap["missing_languages"]),
                        unsafe_allow_html=True)
        st.caption("Soft skills are usually shown through experience; languages are listed separately.")
    _spacer()

if gap.get("explanation"):
    with st.expander("Why these skills matter"):
        st.write(gap["explanation"])
    _spacer()
elif gap.get("explanation_note"):
    # UC008 alt flow 8.1: the skill match itself is still shown above; only the explanation failed.
    st.warning(gap["explanation_note"])
    _spacer()

if st.button("Practise interview for this role", type="primary", key="sm_interview"):
    start_interview(jid)
