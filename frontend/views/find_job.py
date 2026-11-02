import html

import streamlit as st

from frontend.common import (
    call, company_avatar, get_latest_resume, match_badge, nav, page_header, pills, require_login,
    select_job, start_interview,
)

require_login()
PAGE_SIZE = 20

if "find_tab" not in st.session_state:
    st.session_state["find_tab"] = "Browse All"
if pending := st.session_state.pop("pending_find_tab", None):
    st.session_state["find_tab"] = pending

page_header("Find a Job", "Browse, rank and save entry-level roles")
tab = st.segmented_control(
    "View", ["Browse All", "AI Recommended", "Saved"], key="find_tab", label_visibility="collapsed"
) or "Browse All"

saved_ids = {j["job_id"] for j in call("GET", "/saved-jobs")}
# Browse All and Saved don't compute their own match_pct (that's the AI tab's job) -- this lookup
# lets them still flag a job as AI-recommended if it's in the user's latest stored batch.
recommended_pct = {r["job_id"]: r["match_pct"] for r in call("GET", "/recommendations/latest")}

# Pre-fill the Location filters from the user's profile, once -- setdefault only sets it the
# first time this session, so clearing/editing the filter afterwards is remembered, not overwritten.
profile_location = call("GET", "/profile")["location"]
if profile_location:
    st.session_state.setdefault("find_location", profile_location)
    st.session_state.setdefault("rec_location", profile_location)


def _meta_line(location: str, job_type: str | None) -> str:
    parts = [
        '<span class="material-symbols-outlined" style="font-size:16px;vertical-align:text-bottom;">'
        f'location_on</span> {html.escape(location)}'
    ]
    if job_type:
        parts.append(
            '<span class="material-symbols-outlined" style="font-size:16px;vertical-align:text-bottom;">'
            f'work</span> {html.escape(job_type)}'
        )
    return f'<span style="color:#64748B;font-size:0.85rem;">{"&nbsp;&nbsp;&nbsp;".join(parts)}</span>'


def _empty_state(icon: str, message: str, button_label: str | None = None, button_key: str | None = None) -> bool:
    """A centred placeholder for an empty list: a large Material icon, one line of text, and
    optionally the action button that would fix it."""
    st.markdown(
        f'<div class="g2k-empty-state"><span class="material-symbols-outlined">{icon}</span>'
        f'<div>{html.escape(message)}</div></div>',
        unsafe_allow_html=True,
    )
    if button_label:
        _, mid, _ = st.columns([2, 1, 2])
        with mid:
            return st.button(button_label, type="primary", key=button_key, use_container_width=True)
    return False


def job_card(job: dict, context: str, match_pct: int | None = None, matched: list[str] | None = None) -> None:
    jid = job["job_id"]
    is_saved = jid in saved_ids
    if match_pct is None:
        match_pct = recommended_pct.get(jid)
    with st.container(border=True, key=f"g2k_card_{context}_{jid}"):
        badge_html = match_badge(match_pct, "ai") if match_pct is not None else ""
        st.markdown(
            '<div style="display:flex; align-items:center; gap:0.6rem;">'
            f'{company_avatar(job["company"])}'
            '<div style="flex:1; min-width:0;">'
            f'<div style="font-weight:600;">{html.escape(job["title"])}</div>'
            f'<div style="color:#64748B; font-size:0.85rem;">{html.escape(job["company"])}</div>'
            f'{_meta_line(job["location"], job.get("type"))}'
            '</div>'
            f'<div style="flex-shrink:0;">{badge_html}</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        if job.get("summary"):
            st.write(job["summary"])
        if matched:
            st.caption("Matched skills")
            pills(matched, "match")

        with st.container(horizontal=True, gap="small"):
            if st.button("View Details", key=f"det-{context}-{jid}", icon=":material/visibility:"):
                select_job(jid, "job_details")
            if st.button("View Skill Match", key=f"sm-{context}-{jid}", icon=":material/checklist:"):
                select_job(jid, "skill_match")
            if st.button("Practise Interview", key=f"int-{context}-{jid}", icon=":material/mic:"):
                start_interview(jid)
            if st.button("Saved" if is_saved else "Save", key=f"save-{context}-{jid}",
                         icon=":material/bookmark_added:" if is_saved else ":material/bookmark:",
                         type="primary" if is_saved else "secondary"):
                if is_saved:
                    call("DELETE", f"/saved-jobs/{jid}")
                else:
                    call("POST", "/saved-jobs", json={"job_id": jid})
                st.rerun()


if tab == "Browse All":
    options = call("GET", "/jobs/options")
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    q = c1.text_input("Search", placeholder="Search for titles, companies, or keywords...", key="find_q")
    category = c2.selectbox("Category", ["All"] + options["categories"], key="find_category")
    job_type = c3.selectbox("Job type", ["All"] + options["types"], key="find_type")
    location = c4.text_input("Location", placeholder="e.g. Kuala Lumpur", key="find_location")

    sig = (q, category, job_type, location)
    if st.session_state.get("find_sig") != sig:
        st.session_state["find_sig"] = sig
        st.session_state["find_page"] = 0
    page = st.session_state.get("find_page", 0)

    params = {"limit": PAGE_SIZE, "offset": page * PAGE_SIZE}
    if q:
        params["q"] = q
    if category != "All":
        params["category"] = category
    if job_type != "All":
        params["type"] = job_type
    if location:
        params["location"] = location
    data = call("GET", "/jobs", params=params)

    if not data["items"]:
        _empty_state("search_off", "No jobs match these filters.")
    for job in data["items"]:
        job_card(job, "browse")

    start, end = page * PAGE_SIZE, min((page + 1) * PAGE_SIZE, data["total"])
    p1, p2, p3 = st.columns([1, 3, 1])
    if p1.button("Previous", disabled=page == 0, key="find_prev"):
        st.session_state["find_page"] = page - 1
        st.rerun()
    p2.caption(f"Showing {start + 1 if data['total'] else 0}–{end} of {data['total']} jobs")
    if p3.button("Next", disabled=end >= data["total"], key="find_next"):
        st.session_state["find_page"] = page + 1
        st.rerun()

elif tab == "AI Recommended":
    resume = get_latest_resume()
    if resume is None:
        if _empty_state("upload_file", "Upload your resume to get AI-ranked job recommendations.",
                        "Upload resume", "find_upload"):
            nav("resume")
    else:
        options = call("GET", "/jobs/options")
        c1, c2, c3 = st.columns(3)
        category = c1.selectbox("Category", ["All"] + options["categories"], key="rec_category")
        job_type = c2.selectbox("Job type", ["All"] + options["types"], key="rec_type")
        location = c3.text_input("Location", placeholder="e.g. Kuala Lumpur", key="rec_location")

        payload = {"resume_id": resume["id"], "k": 20}
        if category != "All":
            payload["category"] = category
        if job_type != "All":
            payload["type"] = job_type
        if location:
            payload["location"] = location

        recs = call("POST", "/recommendations", json=payload)
        any_filter = category != "All" or job_type != "All" or bool(location)
        if not recs:
            _empty_state("work_off", "No matching jobs found. Try removing filters." if any_filter else
                         "No recommendations found for your resume.")
        for r in recs:
            job_card(r, "rec", match_pct=r["match_pct"], matched=r["matched_skills"])

else:
    st.caption("Jobs you've bookmarked for later.")
    saved = call("GET", "/saved-jobs")
    if not saved:
        _empty_state("bookmark_border", "No saved jobs yet. Save a role to keep it here.")
    for job in saved:
        job_card(job, "saved")
