"""Load each Streamlit page headlessly against a running backend and report any errors.

Start the backend first (venv/Scripts/uvicorn backend.main:app), then run:
    venv/Scripts/python scripts/test_frontend.py
This does not check layout; open the app in a browser to review it visually.
"""
import sys
from pathlib import Path

import requests
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

API = "http://127.0.0.1:8000"
TIMEOUT = 60


def ensure_user() -> dict:
    """Register a test account (ignoring "already exists" from a previous run of this script --
    it's meant to be re-run against a persistent backend, unlike test_backend.py's fresh temp
    database each run), then log in for a fresh session token. Registering no longer returns a
    token itself (UC001: no auto-login)."""
    email, password = "frontend_test@example.com", "testpass123"
    resp = requests.post(f"{API}/auth/register",
                         json={"name": "Frontend Test", "email": email, "password": password})
    if resp.status_code not in (201, 409):
        resp.raise_for_status()
    resp = requests.post(f"{API}/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json()


def first_job_id(headers: dict) -> int:
    return requests.get(f"{API}/jobs?limit=1", headers=headers).json()["items"][0]["job_id"]


def upload_sample_resume(headers: dict) -> int:
    with open(ROOT / "data" / "sample_resume.pdf", "rb") as f:
        resp = requests.post(f"{API}/resumes", files={"file": ("sample_resume.pdf", f, "application/pdf")},
                             headers=headers)
    resp.raise_for_status()
    return resp.json()["id"]


def make_interview(job_id: int, headers: dict) -> dict:
    resp = requests.post(f"{API}/interviews", json={"job_id": job_id, "n": 1}, headers=headers)
    resp.raise_for_status()
    return resp.json()


def run_page(path: Path, state: dict) -> list[str]:
    at = AppTest.from_file(str(path), default_timeout=TIMEOUT)
    for key, value in state.items():
        at.session_state[key] = value
    at.run()
    return [e.value for e in at.exception]


def main() -> None:
    try:
        requests.get(f"{API}/jobs/options", timeout=5)
    except requests.RequestException:
        sys.exit("Backend not reachable at " + API + ". Start it first.")

    user = ensure_user()
    headers = {"Authorization": f"Bearer {user['token']}"}
    job_id = first_job_id(headers)
    upload_sample_resume(headers)
    interview_session = make_interview(job_id, headers)
    session_id = interview_session["id"]

    views = ROOT / "frontend" / "views"
    login_state = {"token": user["token"], "user_id": user["id"],
                   "user_name": user["name"], "user_email": user["email"]}
    # login.py/register.py are tested logged-out (their normal case) -- the rest need login_state,
    # since every other page now gates on require_login().
    cases = {
        "login.py": {},
        "register.py": {},
        "dashboard.py": login_state,
        "find_job.py": login_state,
        "profile.py": login_state,
        "resume.py": login_state,
        "job_details.py": {**login_state, "selected_job_id": job_id},
        "skill_match.py": {**login_state, "selected_job_id": job_id},
        "interview.py": {
            **login_state,
            "interview": interview_session,
            "interview_answers": {},
            "q_index": 0,
        },
        "feedback_report.py": {**login_state, "report_session_id": session_id},
        "interview_history.py": login_state,
    }

    failures = 0
    for name, state in cases.items():
        errors = run_page(views / name, state)
        status = "ok" if not errors else "FAILED"
        print(f"{name:24s} {status}")
        for err in errors:
            failures += 1
            print("   ", err[:300])

    print("\nAll pages loaded without exceptions." if failures == 0 else f"\n{failures} exception(s).")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
