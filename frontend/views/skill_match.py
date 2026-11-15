import html

import streamlit as st

from frontend.common import (
    call, display_skill, donut, get_latest_resume, nav, page_header, pills, require_login,
    start_interview, upload_prompt,
)


def _skill_row(label_html: str, by_type: dict | None, kind: str, empty_text: str) -> None:
    """One "✓ Matched"/"✗ Missing" row of pills. "Software & tools"/"Technical skills"
    subheadings are shown only when BOTH groups are non-empty; otherwise the pills run
    together with no label."""
    st.markdown(label_html, unsafe_allow_html=True)
    by_type = by_type or {}
    software = by_type.get("software") or []
    technical = by_type.get("technical") or []
    if not software and not technical:
        st.caption(empty_text)
        return
    if software and technical:
        st.caption("Software & tools")
        pills(software, kind)
        st.caption("Technical skills")
        pills(technical, kind)
    else:
        pills(software + technical, kind)


def _pill_html(items: list[str], kind: str) -> str:
    return " ".join(f'<span class="g2k-pill g2k-{kind}">{html.escape(display_skill(i))}</span>' for i in items)


def _other_skills_group(title: str, matched: list[str], missing: list[str]) -> None:
    st.markdown(f'<div style="font-weight:700; font-size:0.95rem; margin-bottom:0.4rem;">{html.escape(title)}</div>',
                unsafe_allow_html=True)
    if matched:
        st.markdown(
            '<div style="margin-bottom:0.3rem;"><span style="color:#166534; font-weight:600;">'
            f'✓ Matched:</span> {_pill_html(matched, "match")}</div>',
            unsafe_allow_html=True,
        )
    if missing:
        st.markdown(
            '<div><span style="color:#92400E; font-weight:600;">✗ Missing:</span> '
            f'{_pill_html(missing, "missing")}</div>',
            unsafe_allow_html=True,
        )


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

# Summary: donut + match count + matched/missing pills, all in one card.
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
            st.plotly_chart(donut(gap["match_pct"], "Skill Match", height=150), use_container_width=True,
                            config={"displayModeBar": False})
        with s_col:
            total = len(gap["matched"]) + len(gap["missing"])
            if total:
                st.markdown(f"**{len(gap['matched'])} of {total} required skills matched**")
            _skill_row('<span style="color:#166534; font-weight:600;">✓ Matched</span>',
                       gap.get("matched_by_type"), "match", "None yet")
            _skill_row('<span style="color:#92400E; font-weight:600;">✗ Missing</span>',
                       gap.get("missing_by_type"), "missing", "None missing")

st.caption("Score is based on software and technical skills.")
_spacer()

has_soft = bool(gap.get("soft_skills_required"))
has_languages = bool(gap["matched_languages"] or gap["missing_languages"])
if has_soft or has_languages:
    with st.container(border=True):
        st.subheader("Other skills")
        if has_soft:
            soft_listed = set(gap.get("soft_skills_listed") or [])
            soft_missing = [s for s in gap["soft_skills_required"] if s not in soft_listed]
            _other_skills_group("Soft skills", gap.get("soft_skills_listed") or [], soft_missing)
        if has_soft and has_languages:
            st.markdown('<hr style="margin:0.75rem 0; border-color:#E5E7EB;">', unsafe_allow_html=True)
        if has_languages:
            _other_skills_group("Languages", gap["matched_languages"], gap["missing_languages"])
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
