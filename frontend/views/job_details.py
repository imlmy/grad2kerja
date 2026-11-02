import html
import re

import streamlit as st

from frontend.common import (
    call, company_avatar, format_date, get_latest_resume, match_badge, nav, pills,
    require_login, soft, start_interview,
)

require_login()
jid = st.session_state.get("selected_job_id")
if jid is None:
    st.info("Pick a job from Find a Job first.")
    if st.button("Back to jobs", key="jd_back_empty"):
        nav("find_job")
    st.stop()

_HEADING_WORDS = {
    "job description", "responsibilities", "job responsibilities", "requirements",
    "qualifications", "skills", "what we offer", "benefits", "about us",
}
_BULLET_RE = re.compile(r"^\s*(?:[•\-\*]|\d+\.)\s+")


def _is_heading(line: str) -> bool:
    words = line.split()
    if not words or len(words) > 6:
        return False
    if line.endswith(":"):
        return True
    return line.rstrip(":").lower() in _HEADING_WORDS


def _parse_description(text: str) -> list[dict]:
    """Split a description into {"type": "heading"|"bullets"|"paragraph", ...} blocks. Falls
    back to blank-line paragraphs if the text has no recognisable headings at all."""
    lines = text.split("\n")
    if not any(_is_heading(line.strip()) for line in lines if line.strip()):
        return [{"type": "paragraph", "text": p.strip()}
                for p in re.split(r"\n\s*\n", text) if p.strip()]

    blocks: list[dict] = []
    para_lines: list[str] = []
    bullet_items: list[str] | None = None

    def flush_para():
        if para_lines:
            blocks.append({"type": "paragraph", "text": " ".join(para_lines)})
            para_lines.clear()

    def flush_bullets():
        nonlocal bullet_items
        if bullet_items:
            blocks.append({"type": "bullets", "items": bullet_items})
        bullet_items = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_para()
        elif _is_heading(stripped):
            flush_para()
            flush_bullets()
            blocks.append({"type": "heading", "text": stripped.rstrip(":")})
        elif _BULLET_RE.match(stripped):
            flush_para()
            bullet_items = bullet_items or []
            bullet_items.append(_BULLET_RE.sub("", stripped))
        else:
            flush_bullets()
            para_lines.append(stripped)
    flush_para()
    flush_bullets()
    return blocks


def _highlight_skills(text: str, job_skills: list[str], resume_skills: set[str]) -> str:
    """HTML-escape text and wrap any dictionary skill it contains in a green (on the resume) or
    amber (missing) highlight -- a visual aid, not a re-run of the skill-matching logic."""
    escaped = html.escape(text)
    terms = sorted({s for s in job_skills if s}, key=len, reverse=True)
    if not terms:
        return escaped
    pattern = re.compile(r"(?<!\w)(" + "|".join(re.escape(t) for t in terms) + r")(?!\w)", re.IGNORECASE)

    def repl(m: re.Match) -> str:
        cls = "g2k-hl-match" if m.group(1).lower() in resume_skills else "g2k-hl-missing"
        return f'<span class="{cls}">{m.group(1)}</span>'

    return pattern.sub(repl, escaped)


def _render_description(blocks: list[dict], job_skills: list[str], resume_skills: set[str]) -> None:
    for block in blocks:
        if block["type"] == "heading":
            st.markdown(f"**{html.escape(block['text'])}**")
        elif block["type"] == "bullets":
            items = "".join(
                f"<li>{_highlight_skills(item, job_skills, resume_skills)}</li>" for item in block["items"]
            )
            st.markdown(f"<ul>{items}</ul>", unsafe_allow_html=True)
        else:
            st.markdown(_highlight_skills(block["text"], job_skills, resume_skills), unsafe_allow_html=True)


def _truncate_at_word(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_space = cut.rfind(" ")
    if last_space > 0:
        cut = cut[:last_space]
    return cut.rstrip() + "…"


@st.dialog("Are you ready to apply?")
def _apply_dialog(jid: int, job_match: dict | None, resume: dict | None) -> None:
    """A readiness check followed by a clearly-labelled demo confirmation. Nothing here is
    stored or sent -- the skill match used is either the already-stored row for this job, or
    computed live without saving (see GET /skill-gap/{job_id}), so opening this never changes
    the dashboard's "latest skill match"."""
    if st.session_state.get("apply_confirmed"):
        st.success("✅ Applied")
        st.info("This confirmation demonstrates the intended application workflow. No application "
                 "has been sent to the employer. Applying directly through Grad2Kerja will be "
                 "available in a future version.")
        if st.button("Close", key="apply_close", icon=":material/close:"):
            st.session_state["show_apply_dialog"] = False
            st.rerun()
        return

    if resume is None:
        st.write("Upload your resume to see your match.")
        if st.button("Upload resume", type="primary", key="apply_upload", icon=":material/upload_file:"):
            st.session_state["show_apply_dialog"] = False
            nav("resume")
        return

    st.write(f"**Overall match:** {job_match['match_pct']}% match")

    gap, _ = soft("GET", f"/skill-gap/{jid}")
    needs_practice = False
    if gap is not None:
        total = len(gap["matched"]) + len(gap["missing"])
        st.write(f"**Skill match:** {len(gap['matched'])} of {total} skills")
        if gap["missing"]:
            st.caption("Top missing skills")
            pills(gap["missing"][:3], "missing")
        if total and len(gap["matched"]) / total * 100 < 60:
            needs_practice = True

    interviews, _ = soft("GET", "/interviews")
    scored = [s for s in (interviews or []) if s["job_id"] == jid and s["overall_score"] is not None]
    if scored:
        st.write(f"**Interview practice:** {scored[0]['overall_score']}/100")
    else:
        st.write("**Interview practice:** Not practised yet")
        needs_practice = True

    if needs_practice:
        with st.container(horizontal=True, gap="small"):
            if st.button("Check Skill Match", key="apply_skill_match", icon=":material/checklist:"):
                st.session_state["show_apply_dialog"] = False
                st.session_state["selected_job_id"] = jid
                nav("skill_match")
            if st.button("Practise Interview", key="apply_practise", icon=":material/mic:"):
                st.session_state["show_apply_dialog"] = False
                start_interview(jid)

    if st.button("Apply", type="primary", key="apply_confirm", icon=":material/send:"):
        st.session_state["apply_confirmed"] = True
        st.rerun()


job = call("GET", f"/jobs/{jid}")
saved_ids = {j["job_id"] for j in call("GET", "/saved-jobs")}
recommended_pct = {r["job_id"]: r["match_pct"] for r in call("GET", "/recommendations/latest")}
is_saved = jid in saved_ids


def _format_list(items: list[str]) -> str:
    items = [i.title() for i in items]
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


if st.button("Back to jobs", key="jd_back", icon=":material/arrow_back:"):
    nav("find_job")

resume = get_latest_resume()
job_match = None
if resume is not None:
    job_match = call("GET", f"/jobs/{jid}/match")

_match_help = ("A semantic match of your whole resume against this job's full description -- "
               "not the skills-only percentage shown on Skill Match.")
badge_html = (
    f'<span title="{html.escape(_match_help)}">{match_badge(job_match["match_pct"], "ai")}</span>'
    if job_match is not None else ""
)
st.markdown(
    '<div style="display:flex; align-items:center; gap:0.75rem;">'
    f'{company_avatar(job["company"])}'
    '<div style="flex:1; min-width:0;">'
    f'<div style="font-size:1.6rem; font-weight:700; line-height:1.2;">{html.escape(job["title"])}</div>'
    f'<div style="color:#64748B;">{html.escape(job["company"])} · {html.escape(job["location"])}</div>'
    '</div>'
    f'<div style="flex-shrink:0;">{badge_html}</div>'
    '</div>',
    unsafe_allow_html=True,
)

tags = [f'<span class="g2k-pill g2k-neutral">{job["type"] or "Full time"}</span>',
        f'<span class="g2k-pill g2k-neutral">{job["category"]}</span>']
if job_match is not None and jid in recommended_pct:
    tags.append('<span class="g2k-pill g2k-neutral">✨ AI Recommended</span>')
st.markdown(" ".join(tags), unsafe_allow_html=True)

# AI Insight: a template filled from the semantic match, not an LLM call -- cheap, instant, and
# never overwrites the dashboard's stored skill match (that's a separate, deliberate action on
# the Skill Match page, not something this page should trigger as a side effect).
if resume is None:
    with st.container(border=True):
        st.write("Upload your resume to see how well you match this role.")
        if st.button("Upload resume", type="primary", key="jd_upload", icon=":material/upload_file:"):
            nav("resume")
elif job_match is not None:
    pct = job_match["match_pct"]
    top_skills = job_match["matched_skills"][:3]
    insight = f"You have a {pct}% overall match for this role based on your resume."
    if top_skills:
        insight += (f" Your skills in {_format_list(top_skills)} particularly stand out — "
                    "check your Skill Match for a detailed breakdown.")
    st.info(insight)

left, right = st.columns([3, 2], gap="large")
with left:
    with st.container(border=True):
        st.subheader("Job description")
        description = job["description"] or ""
        resume_skill_set = {s.lower() for s in resume["skills"]} if resume else set()
        if not description:
            st.write("No description provided.")
        elif len(description) <= 600:
            _render_description(_parse_description(description), job["skills"], resume_skill_set)
        else:
            st.write(_truncate_at_word(description, 600))
            with st.expander("Show full description"):
                _render_description(_parse_description(description), job["skills"], resume_skill_set)
    with st.container(border=True):
        st.subheader("Requirements")
        pills(job["skills"], "neutral")

def _info_row(icon: str, label: str, value: str) -> None:
    st.markdown(
        f'<div style="display:flex; align-items:center; gap:0.35rem;">'
        f'<span class="material-symbols-outlined" style="font-size:18px; color:#64748B;">{icon}</span>'
        f'<span class="g2k-caption" style="margin:0;">{html.escape(label)}</span></div>'
        f'<div style="margin-left:1.5rem; margin-bottom:0.5rem;"><strong>{html.escape(str(value))}</strong></div>',
        unsafe_allow_html=True,
    )


with right:
    with st.container(border=True):
        _info_row("payments", "Salary", job["salary"] or "Not stated")
        _info_row("location_on", "Location", job["location"])
        _info_row("military_tech", "Experience level", "Entry level")
        _info_row("calendar_today", "Listed", format_date(job["listing_date"]) or "Not stated")

    if st.button("Apply Now", type="primary", key="jd_apply", use_container_width=True,
                 icon=":material/send:"):
        st.session_state["apply_confirmed"] = False
        st.session_state["show_apply_dialog"] = True
    if st.session_state.get("show_apply_dialog"):
        _apply_dialog(jid, job_match, resume)

    with st.container(horizontal=True, gap="small"):
        if st.button("View Skill Match", key="jd_skill", icon=":material/checklist:"):
            nav("skill_match")
        if st.button("Practise Interview", key="jd_interview", icon=":material/mic:"):
            start_interview(jid)
        if st.button("Saved" if is_saved else "Save", key="jd_save",
                     icon=":material/bookmark_added:" if is_saved else ":material/bookmark:",
                     type="primary" if is_saved else "secondary"):
            if is_saved:
                call("DELETE", f"/saved-jobs/{jid}")
            else:
                call("POST", "/saved-jobs", json={"job_id": jid})
            st.rerun()
