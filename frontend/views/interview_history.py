import streamlit as st

from frontend.common import call, format_date, nav, page_header, require_login

PAGE_SIZE = 10

require_login()
if st.button("Back", key="ih_back", icon=":material/arrow_back:"):
    nav("dashboard")
page_header("Interview History", "Track your progress across mock interviews")

sessions = call("GET", "/interviews")
if not sessions:
    st.info("You have not completed any mock interviews yet.")
    if st.button("Go to Find a Job", key="ih_empty"):
        nav("find_job")
    st.stop()

page = st.session_state.get("ih_page", 0)
start, end = page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE
total = len(sessions)

for s in sessions[start:end]:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([4, 2, 2, 2])
        with c1:
            st.markdown(f"**{s['job_title'] or 'Unknown role'}**")
            st.caption(s["company"] or "")
        with c2:
            st.caption("DATE COMPLETED")
            st.write(format_date(s["created_at"]))
        with c3:
            st.caption("OVERALL SCORE")
            if s["overall_score"] is not None:
                st.write(f"{s['overall_score']}/100")
                st.progress(s["overall_score"] / 100)
            else:
                st.write("In progress")
        with c4:
            if st.button("View Report", key=f"ih_report_{s['id']}"):
                st.session_state["report_session_id"] = s["id"]
                nav("feedback_report")

p1, p2, p3 = st.columns([1, 3, 1])
if p1.button("Previous", disabled=page == 0, key="ih_prev"):
    st.session_state["ih_page"] = page - 1
    st.rerun()
p2.caption(f"Showing {min(end, total)} of {total} interview sessions")
if p3.button("Next", disabled=end >= total, key="ih_next"):
    st.session_state["ih_page"] = page + 1
    st.rerun()
