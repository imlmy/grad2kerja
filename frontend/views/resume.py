import html
import re

import streamlit as st

from frontend.common import ApiError, api, call, nav, page_header, pills, require_login

require_login()
MAX_BYTES = 5 * 1024 * 1024
_BLANK_LINE = re.compile(r"\n\s*\n")

_MONTH_YEAR = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}"
_ENTRY_DATE_RANGE = re.compile(
    rf"(?P<date>{_MONTH_YEAR}\s*(?:-|–|—|to)\s*(?:{_MONTH_YEAR}|Present|Current))\s*$", re.IGNORECASE,
)


def _text_to_list(text: str) -> list[str]:
    return [b.strip() for b in _BLANK_LINE.split(text) if b.strip()]


def _split_title_date(line: str) -> tuple[str, str | None]:
    """Pull a trailing date range (e.g. "Jun 2026 - Dec 2026") off an entry's title line, so it
    can be shown separately on the right instead of as part of the title text."""
    m = _ENTRY_DATE_RANGE.search(line)
    if not m:
        return line.strip(), None
    return line[:m.start()].rstrip(" -–—|").strip(), m.group("date").strip()


def _looks_like_tool_list(line: str) -> bool:
    """Heuristic for a comma-separated list of tools/technologies (e.g. "Python, Streamlit,
    FastAPI, spaCy, SQLite") rather than a prose sentence: at least 3 comma-separated parts, each
    short enough to be a tool name rather than a clause."""
    parts = [p.strip() for p in line.strip().rstrip(".").split(",")]
    return len(parts) >= 3 and all(p and len(p.split()) <= 4 for p in parts)


def _view_entries(entries: list[str]) -> None:
    if not entries:
        st.caption("No entries yet.")
        return
    for i, entry in enumerate(entries):
        lines = [line.strip() for line in entry.split("\n") if line.strip()]
        if not lines:
            continue
        title, date = _split_title_date(lines[0])
        header = f'<div style="font-weight:700;">{html.escape(title)}</div>'
        if date:
            header = (
                '<div style="display:flex; justify-content:space-between; align-items:baseline; gap:0.75rem;">'
                f'<div style="font-weight:700;">{html.escape(title)}</div>'
                f'<div style="color:#64748B; font-size:0.85rem; white-space:nowrap;">{html.escape(date)}</div>'
                '</div>'
            )
        st.markdown(header, unsafe_allow_html=True)
        for line in lines[1:]:
            if _looks_like_tool_list(line):
                st.markdown(f'<div style="color:#64748B; font-size:0.85rem;">{html.escape(line)}</div>',
                            unsafe_allow_html=True)
            else:
                st.markdown(f"- {line}")
        if i < len(entries) - 1:
            st.markdown('<hr style="margin:0.6rem 0; border-color:#E5E7EB;">', unsafe_allow_html=True)


def _card(col, title: str, rid: int, key: str, parsed: dict, view_fn, widget_fn, to_value=lambda v: v) -> None:
    """One resume section as a bordered card with its own Edit/Save/Cancel, so editing one
    section doesn't require touching the others."""
    editing_key = f"editing_{key}_{rid}"
    widget_key = f"widget_{key}_{rid}"
    editing = st.session_state.get(editing_key, False)
    with col:
        with st.container(border=True):
            h1, h2 = st.columns([6, 1], vertical_alignment="center")
            h1.markdown(f"**{title}**")
            if not editing:
                if h2.button("", key=f"edit_{key}_{rid}", icon=":material/edit:", help="Edit"):
                    st.session_state[editing_key] = True
                    st.rerun()
                view_fn(parsed[key])
            else:
                widget_fn(widget_key, parsed[key])
                s1, s2 = st.columns(2)
                if s1.button("Save", type="primary", key=f"save_{key}_{rid}"):
                    value = to_value(st.session_state[widget_key])
                    updated = call("PATCH", f"/resumes/{rid}", json={key: value})
                    st.session_state["parsed_resume"] = updated
                    st.session_state[editing_key] = False
                    st.rerun()
                if s2.button("Cancel", key=f"cancel_{key}_{rid}"):
                    st.session_state[editing_key] = False
                    st.rerun()


def _spacer() -> None:
    st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)


page_header(
    "Upload Your Resume",
    "We'll extract your skills, languages, education, experience and projects to match you "
    "with suitable roles. Review and edit anything that looks off before continuing.",
)
if st.button("Back to dashboard", key="rs_back", icon=":material/arrow_back:"):
    nav("dashboard")

uploaded = st.file_uploader(
    "Drag and drop your resume here, or click to browse (PDF only, max 5MB)",
    type=["pdf"],
    key="resume_file",
)
too_big = uploaded is not None and uploaded.size > MAX_BYTES
if too_big:
    st.error("This file is larger than 5MB. Please upload a smaller PDF.")

if st.button("Parse resume", type="primary", disabled=uploaded is None or too_big, key="rs_parse"):
    st.session_state["parsed_resume"] = call(
        "POST", "/resumes",
        files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
    )

# Arriving here via Profile's "Update resume" (no fresh upload this session): load the existing
# resume so the same sections and editing flow are available, not just right after a new upload.
if "parsed_resume" not in st.session_state:
    try:
        st.session_state["parsed_resume"] = api("GET", "/resumes/latest")
    except ApiError:
        st.session_state["parsed_resume"] = None

parsed = st.session_state.get("parsed_resume")

if parsed:
    st.success("Your resume has been processed. Review the details below before continuing.")
    rid = parsed["id"]

    row1 = st.columns(2, gap="medium")
    _card(row1[0], "Skills", rid, "skills", parsed,
          view_fn=lambda v: pills(v, "match"),
          widget_fn=lambda k, v: st.multiselect("Skills", options=v, default=v,
                                                 accept_new_options=True, key=k))
    _card(row1[1], "Languages", rid, "languages", parsed,
          view_fn=lambda v: pills(v, "neutral"),
          widget_fn=lambda k, v: st.multiselect("Languages", options=v, default=v,
                                                 accept_new_options=True, key=k))
    _spacer()
    _card(st.container(), "Education", rid, "education", parsed,
          view_fn=_view_entries,
          widget_fn=lambda k, v: st.text_area(
              "Education", value="\n\n".join(v), height=160, key=k,
              help="Separate entries with a blank line.",
          ),
          to_value=_text_to_list)
    _spacer()
    _card(st.container(), "Experience", rid, "experience", parsed,
          view_fn=_view_entries,
          widget_fn=lambda k, v: st.text_area(
              "Experience", value="\n\n".join(v), height=160, key=k,
              help="Separate entries with a blank line.",
          ),
          to_value=_text_to_list)
    _spacer()
    _card(st.container(), "Projects", rid, "projects", parsed,
          view_fn=_view_entries,
          widget_fn=lambda k, v: st.text_area(
              "Projects", value="\n\n".join(v), height=160, key=k,
              help="Separate entries with a blank line.",
          ),
          to_value=_text_to_list)
    _spacer()

    if st.button("Continue to Job Matches", type="primary", key="rs_continue"):
        # Any card still mid-edit has an unsaved value in its widget's session state -- fold
        # those into one PATCH (same shape each card's own Save button sends) before leaving.
        pending = {}
        for field in ("skills", "languages"):
            if st.session_state.get(f"editing_{field}_{rid}"):
                widget_key = f"widget_{field}_{rid}"
                if widget_key in st.session_state:
                    pending[field] = st.session_state[widget_key]
        for field in ("education", "experience", "projects"):
            if st.session_state.get(f"editing_{field}_{rid}"):
                widget_key = f"widget_{field}_{rid}"
                if widget_key in st.session_state:
                    pending[field] = _text_to_list(st.session_state[widget_key])
        if pending:
            st.session_state["parsed_resume"] = call("PATCH", f"/resumes/{rid}", json=pending)
            for field in pending:
                st.session_state[f"editing_{field}_{rid}"] = False
        st.session_state["pending_find_tab"] = "AI Recommended"
        nav("find_job")
