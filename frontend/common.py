"""Shared helpers for the Streamlit pages: backend client, navigation, styling and small widgets."""
import html
import os
from datetime import datetime

import requests
import streamlit as st

BASE_URL = os.getenv("GRAD2KERJA_API", "http://127.0.0.1:8000")
START_HINT = "Cannot reach the backend. Start it with: venv/Scripts/uvicorn backend.main:app --reload"


def format_date(value: str | None) -> str:
    """Parse a date/datetime string (sqlite "YYYY-MM-DD[ HH:MM:SS]", ISO with a timezone offset,
    or a bare "YYYY-MM-DD") and format it as "28 July 2026" -- the one date format used
    everywhere in the UI. Returns the original value unchanged if it can't be parsed."""
    if not value:
        return ""
    try:
        dt = datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except ValueError:
        return str(value)
    return f"{dt.day} {dt.strftime('%B')} {dt.year}"

STYLE = """
<style>
.g2k-pill { 
    display:inline-block; 
    padding:2px 10px; 
    border-radius:999px; 
    font-size:0.82rem;
    margin:2px 4px 2px 0; 
    font-weight:500;
}
.g2k-match {
    background:#DCFCE7; 
    color:#166534;
}
.g2k-missing {
    background:#FEF3C7; 
    color:#92400E;
}
.g2k-neutral {
    background:#E0E7FF; 
    color:#0B3FB8;
}
.g2k-score {
    font-size:2.6rem; 
    font-weight:700; 
    color:#0B3FB8; 
    line-height:1.1;
}
.g2k-score span {
    font-size:1.1rem; 
    color:#64748B; 
    font-weight:500;
}
.g2k-caption {
    font-size:0.75rem; 
    letter-spacing:0.06em; 
    text-transform:uppercase; 
    color:#64748B;
}
.st-key-g2k_refine_profile {
    border: 2px dashed #94A3B8; 
    border-radius: 12px; 
    padding: 1.25rem 1.5rem;
}
.g2k-hl-match {
    background:#DCFCE7; 
    color:#166534; 
    border-radius:4px; 
    padding:0 3px;
}
.g2k-hl-missing {
    background:#FEF3C7; 
    color:#92400E; 
    border-radius:4px; 
    padding:0 3px;
}
</style>
"""

AUTH_STYLE = """
<style>
[data-testid="stHeader"] {display: none;}
.block-container {
    padding-top: 0 !important; 
    padding-bottom: 0 !important;
    max-width: 100% !important; 
    padding-left: 0 !important; 
    padding-right: 0 !important;
}
.st-key-g2k_auth_left {
    background: #0B3FB8; 
    min-height: 100vh; 
    display: flex; 
    align-items: center; 
    flex-direction: column; 
    justify-content: center;
    padding: 4rem 3rem;
}
.st-key-g2k_auth_left h1 {
    color: #FFFFFF; 
    font-size: 4rem; 
    font-weight: 800; 
    line-height: 1.1;
    margin: 0 0 1rem 0;
}
.st-key-g2k_auth_left h1 .g2k-auth-green {
    color: #22C55E;
}
.st-key-g2k_auth_left p {
    color: #DBEAFE; 
    font-size: 1.35rem; 
    max-width: 520px; 
    line-height: 1.5; 
    margin: 0;
}
.st-key-g2k_auth_right {
    display: flex; 
    align-items: center; 
    justify-content: center;
    min-height: 100vh; 
    padding: 2rem;
}
.g2k-auth-card-head h2 {
    font-size: 1.9rem; 
    margin: 0 0 0.3rem 0;}
.g2k-auth-card-head .g2k-auth-sub {
    color: #64748B; 
    margin: 0 0 1.5rem 0; 
    font-size: 0.95rem;}
</style>
"""

class ApiError(Exception):
    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status


def api(method: str, path: str, **kwargs):
    """Call the backend and return parsed JSON. Raises ApiError on failure. Attaches the logged-in
    session's token as a bearer header automatically -- every endpoint except /auth/register and
    /auth/login requires it."""
    headers = kwargs.pop("headers", None) or {}
    token = st.session_state.get("token")
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.request(method, BASE_URL + path, timeout=180, headers=headers, **kwargs)
    except requests.RequestException as e:
        raise ApiError(START_HINT, 0) from e
    if resp.status_code >= 400:
        try:
            detail = resp.json()["detail"]
        except (ValueError, KeyError, TypeError):
            detail = resp.text or resp.reason
        raise ApiError(str(detail), resp.status_code)
    return resp.json()


def call(method: str, path: str, **kwargs):
    """Like api(), but shows the error and stops the page. Use for required data."""
    try:
        return api(method, path, **kwargs)
    except ApiError as e:
        st.error(str(e))
        st.stop()


def soft(method: str, path: str, **kwargs):
    """Like api(), but returns (data, error) so a failing section doesn't stop the page."""
    try:
        return api(method, path, **kwargs), None
    except ApiError as e:
        return None, str(e)


def get_latest_resume() -> dict | None:
    try:
        return api("GET", "/resumes/latest")
    except ApiError as e:
        if e.status == 404:
            return None
        st.error(str(e))
        st.stop()


def nav(key: str) -> None:
    st.switch_page(st.session_state["pages"][key])


def require_login() -> int:
    """Gate a page behind login. Call this first, before any other backend call on the page."""
    if st.session_state.get("token") is None:
        st.info("Please log in to continue.")
        if st.button("Go to Log In", key="require_login"):
            nav("login")
        st.stop()
    return st.session_state.get("user_id")


def logout() -> None:
    """End the session on the backend (deletes the token), then clear all session state (so
    nothing from this account leaks into the next login in the same browser tab) and return to
    the login page."""
    soft("POST", "/auth/logout")  # best-effort -- log out locally either way
    login_page = st.session_state["pages"]["login"]
    st.session_state.clear()
    st.switch_page(login_page)


def start_interview(job_id: int) -> None:
    session, err = soft("POST", "/interviews", json={"job_id": job_id, "n": 5})
    if session is None:
        st.error("Interview questions are temporarily unavailable. Try again later.")
        st.caption(err)
        st.stop()
    st.session_state["interview"] = session
    st.session_state["interview_answers"] = {}
    st.session_state["q_index"] = 0
    nav("interview")


def upload_prompt(message: str) -> None:
    """Show a prompt to upload a resume, then stop the page."""
    with st.container(border=True):
        st.write(message)
        if st.button("Upload resume", type="primary", key="upload_prompt"):
            nav("resume")
    st.stop()


def select_job(job_id: int, page_key: str) -> None:
    st.session_state["selected_job_id"] = job_id
    nav(page_key)


def page_header(title: str, subtitle: str | None = None) -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def pills(items: list[str], kind: str) -> None:
    if not items:
        st.caption("None")
        return
    tags = " ".join(f'<span class="g2k-pill g2k-{kind}">{html.escape(i.title())}</span>' for i in items)
    st.markdown(tags, unsafe_allow_html=True)


def score_label(score_10: float) -> str:
    if score_10 >= 8:
        return "Strong performance"
    if score_10 >= 5:
        return "Solid performance, with a few areas to sharpen"
    return "Needs more practice"


def overall_label(score_100: int) -> str:
    if score_100 >= 80:
        return "Strong performance"
    if score_100 >= 60:
        return "Solid performance, with a few areas to sharpen before your real interview"
    return "Keep practising and focus on the areas below"


def apply_style() -> None:
    st.markdown(STYLE, unsafe_allow_html=True)


def auth_layout():
    """Shared chrome for the login/register pages (A3 figures 1-2): hides the app's top nav and
    lays out a deep-blue hero panel on the left against the Grad2Kerja card heading on the right.
    Returns the right panel's container -- the caller renders its own form inside it."""
    st.markdown(AUTH_STYLE, unsafe_allow_html=True)
    left, right = st.columns([1, 1], gap="small")
    with left:
        with st.container(key="g2k_auth_left"):
            st.markdown(
                '<h1>From graduate to <span class="g2k-auth-green">hired.</span></h1>'
                "<p>Job matching, skill gap insights, and interview practice "
                "&mdash; built for Malaysia's fresh graduates.</p>",
                unsafe_allow_html=True,
            )
    right_box = right.container(key="g2k_auth_right")
    with right_box:
        _, mid, _ = st.columns([1, 6, 1])
        with mid:
            st.markdown(
                '<div class="g2k-auth-card-head"><h2>\U0001F393 Grad2Kerja</h2>'
                '<p class="g2k-auth-sub">Empowering your career journey into the Malaysian '
                "workforce.</p></div>",
                unsafe_allow_html=True,
            )
            return st.container()
