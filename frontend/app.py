"""Grad2Kerja Streamlit app. Run from the project root:
    venv/Scripts/streamlit run frontend/app.py
"""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from frontend.common import apply_style  # noqa: E402

st.set_page_config(page_title="Grad2Kerja", page_icon="🎓", layout="wide")
apply_style()

VIEWS = Path(__file__).resolve().parent / "views"
logged_in = st.session_state.get("token") is not None
# Pages stay registered either way (nav() can switch_page to a hidden one, e.g. right after
# login succeeds) -- only their top-nav visibility and which one is "default" depends on login.
P = {
    "login": st.Page(VIEWS / "login.py", title="Log In", url_path="login",
                      default=not logged_in, visibility="hidden" if logged_in else "visible"),
    "register": st.Page(VIEWS / "register.py", title="Register", url_path="register",
                         visibility="hidden" if logged_in else "visible"),
    "dashboard": st.Page(VIEWS / "dashboard.py", title="Dashboard", url_path="dashboard",
                          default=logged_in, visibility="visible" if logged_in else "hidden"),
    "find_job": st.Page(VIEWS / "find_job.py", title="Find a Job", url_path="find-a-job",
                         visibility="visible" if logged_in else "hidden"),
    "profile": st.Page(VIEWS / "profile.py", title="Profile", url_path="profile",
                        visibility="visible" if logged_in else "hidden"),
    "resume": st.Page(VIEWS / "resume.py", title="Upload Resume", url_path="resume", visibility="hidden"),
    "job_details": st.Page(VIEWS / "job_details.py", title="Job Details", url_path="job-details", visibility="hidden"),
    "skill_match": st.Page(VIEWS / "skill_match.py", title="Skill Match", url_path="skill-match", visibility="hidden"),
    "interview": st.Page(VIEWS / "interview.py", title="Mock Interview", url_path="mock-interview", visibility="hidden"),
    "feedback_report": st.Page(VIEWS / "feedback_report.py", title="Feedback Report", url_path="feedback-report", visibility="hidden"),
    "interview_history": st.Page(VIEWS / "interview_history.py", title="Interview History", url_path="interview-history", visibility="hidden"),
}
st.session_state["pages"] = P

navigation = st.navigation(list(P.values()), position="top")
navigation.run()
