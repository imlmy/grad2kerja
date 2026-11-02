"""Smoke-test the FastAPI endpoints against a temporary database.

Makes a few real LLM calls (interview questions, one answer evaluation).
Usage: venv/Scripts/python scripts/test_backend.py
"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

tmp_dir = Path(tempfile.mkdtemp())
os.environ["GRAD2KERJA_DB"] = str(tmp_dir / "test.db")

from fastapi.testclient import TestClient  # noqa: E402
from backend.main import app  # noqa: E402


def make_pdf(text: str) -> bytes:
    """Render plain text to a one-page PDF in memory -- for a throwaway test fixture that
    doesn't need its own file in the repo."""
    import io

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(8.27, 11.69))
    fig.text(0.08, 0.95, text, family="monospace", fontsize=11, va="top")
    buf = io.BytesIO()
    fig.savefig(buf, format="pdf")
    plt.close(fig)
    return buf.getvalue()


def call(client, method, url, expect=200, label=None, **kwargs):
    t0 = time.time()
    resp = client.request(method, url, **kwargs)
    elapsed = time.time() - t0
    status = "ok" if resp.status_code == expect else f"FAILED (expected {expect})"
    print(f"{label or method + ' ' + url:55s} {resp.status_code} {elapsed:6.2f}s  {status}")
    if resp.status_code != expect:
        print("   ", resp.text[:300])
        raise SystemExit(1)
    return resp.json()


try:
    t0 = time.time()
    with TestClient(app) as client:
        startup = time.time() - t0
        print(f"backend startup (includes model preload): {startup:.2f}s\n")

        # --- authentication ---
        call(client, "GET", "/resumes/latest", 401, "no Authorization header -> 401")
        call(client, "GET", "/jobs", 401, "no Authorization header -> 401 (jobs now require login)")
        register = call(client, "POST", "/auth/register", 201, "register",
                        json={"name": "Test User", "email": "test@example.com", "password": "testpass123"})
        assert register["email"] == "test@example.com"
        assert "token" not in register, "register should not create a session (UC001: no auto-login)"
        call(client, "POST", "/auth/register", 409, "duplicate email rejected",
             json={"name": "Someone Else", "email": "test@example.com", "password": "anotherpass1"})
        call(client, "POST", "/auth/register", 422, "whitespace-only name rejected",
             json={"name": "   ", "email": "whitespace@example.com", "password": "testpass123"})
        call(client, "POST", "/auth/login", 401, "wrong password rejected",
             json={"email": "test@example.com", "password": "wrongpassword"})
        login_resp = call(client, "POST", "/auth/login", 200, "login",
                          json={"email": "test@example.com", "password": "testpass123"})
        assert login_resp["id"] == register["id"]
        token = login_resp["token"]
        client.headers["Authorization"] = f"Bearer {token}"
        print(f"   registered and logged in as user {login_resp['id']}")

        call(client, "GET", "/resumes/latest", 401, "bogus token rejected",
             headers={"Authorization": "Bearer not-a-real-token"})

        profile = call(client, "GET", "/profile", label="get profile")
        assert profile == {"id": login_resp["id"], "name": "Test User", "email": "test@example.com",
                           "field_of_study": "", "location": ""}
        call(client, "PATCH", "/profile", 422, "edit profile with nothing to update", json={})
        call(client, "PATCH", "/profile", 422, "whitespace-only profile name rejected",
             json={"name": "   "})
        call(client, "PATCH", "/profile", 422, "email is not an editable field",
             json={"email": "someoneelse@example.com"})
        updated_profile = call(client, "PATCH", "/profile", label="edit name, field of study and location",
                               json={"name": "Updated Name", "field_of_study": "Computer Science",
                                     "location": "Petaling Jaya, Selangor"})
        assert updated_profile["name"] == "Updated Name" and updated_profile["email"] == "test@example.com"
        assert updated_profile["field_of_study"] == "Computer Science"
        assert updated_profile["location"] == "Petaling Jaya, Selangor"
        still_set = call(client, "GET", "/profile", label="field of study and location persist")
        assert still_set["field_of_study"] == "Computer Science"
        assert still_set["location"] == "Petaling Jaya, Selangor"
        call(client, "POST", "/profile/password", 404, "change-password endpoint removed")
        print("   profile edit confirmed (name, field of study, location); email not editable")

        no_resume_match = call(client, "GET", "/jobs/74677668/match", label="job match with no resume yet")
        assert no_resume_match is None, "job match should be null (not an error) when there's no resume"

        call(client, "POST", "/resumes", 422, "reject a .txt upload",
             files={"file": ("resume.txt", b"Not a PDF, just plain text.", "text/plain")})
        oversized = b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024 + 1)
        call(client, "POST", "/resumes", 422, "reject an oversized file",
             files={"file": ("big_resume.pdf", oversized, "application/pdf")})
        call(client, "POST", "/resumes", 422, "reject a corrupt PDF",
             files={"file": ("corrupt.pdf", b"%PDF-1.4\nnot actually valid PDF content", "application/pdf")})

        pdf = (ROOT / "data" / "sample_resume.pdf").read_bytes()
        resume = call(client, "POST", "/resumes", 201, "upload resume",
                      files={"file": ("sample_resume.pdf", pdf, "application/pdf")})
        rid = resume["id"]
        assert resume["size_bytes"] == len(pdf), f"expected size_bytes {len(pdf)}, got {resume['size_bytes']}"
        print(f"   skills found: {len(resume['skills'])}, education blocks: {len(resume['education'])}, "
              f"experience blocks: {len(resume['experience'])}, projects blocks: {len(resume['projects'])}")

        fetched = call(client, "GET", f"/resumes/{rid}", label="get resume")
        assert fetched["size_bytes"] == len(pdf)
        call(client, "GET", "/resumes/9999", 404, "get missing resume")

        updated = call(client, "PATCH", f"/resumes/{rid}", label="edit resume skills",
                       json={"skills": ["microsoft excel", "teamwork", "a new skill"]})
        assert updated["skills"] == ["microsoft excel", "teamwork", "a new skill"], updated["skills"]
        assert updated["education"] == resume["education"], "untouched fields should be unchanged"
        call(client, "PATCH", f"/resumes/9999", 404, "edit missing resume", json={"skills": ["x"]})
        call(client, "PATCH", f"/resumes/{rid}", 422, "edit with nothing to update", json={})

        browse = call(client, "GET", "/jobs?category=Accounting&limit=3", label="browse Accounting jobs")
        print(f"   total Accounting jobs: {browse['total']}")
        call(client, "GET", "/jobs/999999999", 404, "get missing job")

        sample_job = browse["items"][0]
        company_hit = call(client, "GET", "/jobs", label="search by company name (not just title)",
                           params={"q": sample_job["company"], "limit": 5})
        assert any(j["job_id"] == sample_job["job_id"] for j in company_hit["items"]), \
            "expected GET /jobs?q=<company> to match on company"
        assert len(sample_job["summary"]) <= 201, \
            f"card summary should be capped at ~200 chars, got {len(sample_job['summary'])}"

        multiline_job_detail = call(client, "GET", "/jobs/74677668", label="get job with a multi-line description")
        assert "\n" in multiline_job_detail["description"], \
            "GET /jobs/{id} should return description_display (line breaks preserved), not the flattened descriptions"

        if sample_job["summary"].endswith("…"):
            full = call(client, "GET", f"/jobs/{sample_job['job_id']}",
                       label="get full description for truncation check")
            prefix = sample_job["summary"][:-1].rstrip()
            assert full["description"].startswith(prefix), \
                "truncated summary should be a prefix of the full description"
            next_char = full["description"][len(prefix):len(prefix) + 1]
            assert next_char in (" ", ""), f"summary was cut mid-word (next char: {next_char!r})"
            print("   summary truncation confirmed at a word boundary")

        t0 = time.time()
        recs = call(client, "POST", "/recommendations", label="recommendations (k=5)",
                    json={"resume_id": rid, "k": 5})
        first_call = time.time() - t0
        top_job = recs[0]["job_id"]
        assert all("match_pct" in r for r in recs), "match_pct missing from a recommendation"
        print(f"   top job: {recs[0]['title']} ({recs[0]['match_pct']}% match)")
        print(f"   first /recommendations call: {first_call:.2f}s (UC006/REQ_F007 requires <5s)")
        assert first_call < 5, f"first recommendation took {first_call:.2f}s, exceeds the 5s requirement"
        call(client, "GET", f"/jobs/{top_job}", label="get top job detail")

        top_match = call(client, "GET", f"/jobs/{top_job}/match", label="job match for the top recommendation")
        assert top_match["match_pct"] == recs[0]["match_pct"], \
            "job match should score the same job identically to recommend_jobs"
        print(f"   job match pct for top recommendation: {top_match['match_pct']}%")

        no_skills_match = call(client, "GET", "/jobs/74677668/match",
                               label="job match for a job with no listed skills")
        assert no_skills_match is not None and no_skills_match["matched_skills"] == [], \
            "a job with no skills should still return a match_pct, with empty matched_skills"
        call(client, "GET", "/jobs/999999999/match", 404, "job match for a missing job")

        latest = call(client, "GET", "/recommendations/latest", label="get stored recommendations")
        assert {r["job_id"] for r in latest} == {r["job_id"] for r in recs}, \
            "stored recommendations don't match the last computed batch"
        assert latest[0]["match_pct"] == max(r["match_pct"] for r in recs)
        print(f"   stored recommendations: {len(latest)}, top match_pct: {latest[0]['match_pct']}%")

        # Filtered calls must not overwrite the stored unfiltered batch.
        filtered = call(client, "POST", "/recommendations", label="filtered recommendations (nonsense location)",
                        json={"resume_id": rid, "k": 5, "location": "zzznowhere"})
        assert filtered == [], f"expected no results for a nonsense location, got {len(filtered)}"
        still_latest = call(client, "GET", "/recommendations/latest", label="get latest after filtered call")
        assert {r["job_id"] for r in still_latest} == {r["job_id"] for r in recs}, \
            "a filtered call changed the stored unfiltered recommendations"
        print(f"   stored recommendations unchanged after filtered call: {len(still_latest)}")

        # Re-uploading a different resume must clear the stored batch -- it was computed from a
        # resume that's no longer "the" resume. The dashboard should then recompute for the new one.
        new_pdf = make_pdf("John Tan\nSKILLS\nPython, SQL, JavaScript, Networking, Project Management\n")
        new_resume = call(client, "POST", "/resumes", 201, "upload a different resume",
                          files={"file": ("other_resume.pdf", new_pdf, "application/pdf")})
        assert new_resume["id"] != rid, "expected a new resume id"
        cleared = call(client, "GET", "/recommendations/latest", label="get latest after re-upload")
        assert cleared == [], f"expected recommendations cleared after re-upload, got {len(cleared)}"

        recomputed = call(client, "POST", "/recommendations", label="dashboard recomputes for new resume",
                          json={"resume_id": new_resume["id"], "k": 2})
        after_recompute = call(client, "GET", "/recommendations/latest", label="get latest after recompute")
        assert {r["job_id"] for r in after_recompute} == {r["job_id"] for r in recomputed}
        print(f"   recommendations recomputed and stored for the new resume: {len(after_recompute)}")

        # Editing skills (not just a fresh upload) must also clear the stored batch.
        call(client, "PATCH", f"/resumes/{new_resume['id']}", label="edit skills after recompute",
             json={"skills": ["python", "sql"]})
        cleared_by_edit = call(client, "GET", "/recommendations/latest", label="get latest after skill edit")
        assert cleared_by_edit == [], f"expected recommendations cleared after skill edit, got {len(cleared_by_edit)}"
        # Editing a field that isn't skills must NOT clear anything (nothing to clear here anyway,
        # but confirms the endpoint doesn't error on a skills-less update after a prior clear).
        call(client, "PATCH", f"/resumes/{new_resume['id']}", label="edit projects only",
             json={"projects": ["A project."]})

        gap = call(client, "POST", "/skill-gap", label="skill gap (no explanation)",
                  json={"resume_id": rid, "job_id": top_job, "explain": False})
        assert gap["explanation"] is None
        assert "matched_languages" in gap and "missing_languages" in gap
        assert "unrecognised_terms" not in gap, "unrecognised_terms should be internal-only now"
        assert gap["missing"], "test setup assumption failed: expected the top job to have a missing skill"

        latest_gap = call(client, "GET", "/skill-gap/latest", label="get latest skill match")
        assert latest_gap["job_id"] == top_job and latest_gap["match_pct"] == gap["match_pct"]
        print(f"   latest skill match stored: job {latest_gap['job_id']}, match_pct {latest_gap['match_pct']}")

        # Apply Now readiness check (GET /skill-gap/{job_id}) must be read-only: using the
        # already-stored row for one job, or computing live for another, must never change the
        # dashboard's stored "latest skill match".
        job_match_stored = call(client, "GET", f"/skill-gap/{top_job}", label="skill-gap-for-job uses the stored row")
        assert job_match_stored["match_pct"] == gap["match_pct"]
        assert job_match_stored["matched"] == gap["matched"] and job_match_stored["missing"] == gap["missing"]
        still_latest = call(client, "GET", "/skill-gap/latest", label="latest skill match unchanged after stored lookup")
        assert still_latest["job_id"] == top_job and still_latest["match_pct"] == gap["match_pct"]

        other_job = recs[1]["job_id"]
        live_gap = call(client, "GET", f"/skill-gap/{other_job}", label="skill-gap-for-job computes live, unstored")
        assert {"match_pct", "matched", "missing"} <= live_gap.keys()
        still_latest2 = call(client, "GET", "/skill-gap/latest", label="latest skill match still unchanged")
        assert still_latest2["job_id"] == top_job, \
            "GET /skill-gap/{job_id} must never change the stored latest skill match"
        print("   GET /skill-gap/{job_id} confirmed read-only: latest skill match unaffected")

        no_skill_job = 74677668  # a real job_id with no skills listed, per the dataset
        gap_no_skills = call(client, "POST", "/skill-gap", label="skill gap for a job with no skills",
                             json={"resume_id": rid, "job_id": no_skill_job})
        assert gap_no_skills["match_pct"] is None
        assert "doesn't list specific skills" in gap_no_skills["message"]

        # UC008 alt flow 8.1: a failing explanation must not lose the skill match result.
        with patch("backend.main.explain_gaps", side_effect=RuntimeError("mocked explanation failure")):
            gap_fail = call(client, "POST", "/skill-gap", label="skill gap with mocked explain failure",
                            json={"resume_id": rid, "job_id": top_job, "explain": True})
        assert gap_fail["matched"] == gap["matched"] and gap_fail["missing"] == gap["missing"]
        assert gap_fail["match_pct"] == gap["match_pct"]
        assert gap_fail["explanation"] is None
        assert "mocked explanation failure" in gap_fail.get("explanation_note", "")
        print(f"   explain failure handled, result kept: explanation_note={gap_fail['explanation_note']!r}")

        # Re-uploading a different resume must also clear stored skill matches.
        third_pdf = make_pdf("Third Person\nSKILLS\nAccounting, Auditing\n")
        third_resume = call(client, "POST", "/resumes", 201, "upload a third resume",
                            files={"file": ("third_resume.pdf", third_pdf, "application/pdf")})
        cleared_sm = call(client, "GET", "/skill-gap/latest", label="get latest skill match after re-upload")
        assert cleared_sm is None, f"expected skill match cleared after re-upload, got {cleared_sm}"

        # Re-establish a stored skill match, then confirm PATCHing skills clears it.
        call(client, "POST", "/skill-gap", label="skill gap for third resume",
             json={"resume_id": third_resume["id"], "job_id": top_job, "explain": False})
        restored = call(client, "GET", "/skill-gap/latest", label="confirm skill match stored again")
        assert restored is not None

        call(client, "PATCH", f"/resumes/{third_resume['id']}", label="edit skills clears skill match",
             json={"skills": ["accounting"]})
        cleared_by_skills = call(client, "GET", "/skill-gap/latest", label="confirm cleared by skills edit")
        assert cleared_by_skills is None

        # And confirm PATCHing languages alone also clears it (recommendations don't care about
        # languages, but check_skill_match does).
        call(client, "POST", "/skill-gap", label="skill gap once more",
             json={"resume_id": third_resume["id"], "job_id": top_job, "explain": False})
        restored_again = call(client, "GET", "/skill-gap/latest", label="confirm stored once more")
        assert restored_again is not None

        call(client, "PATCH", f"/resumes/{third_resume['id']}", label="edit languages clears skill match",
             json={"languages": ["english"]})
        cleared_by_languages = call(client, "GET", "/skill-gap/latest", label="confirm cleared by languages edit")
        assert cleared_by_languages is None
        print("   skill match clearing confirmed for: re-upload, skills edit, languages edit")

        call(client, "POST", "/saved-jobs", 201, "save job", json={"job_id": top_job})
        saved = call(client, "GET", "/saved-jobs", label="list saved jobs")
        print(f"   saved count: {len(saved)}")
        call(client, "DELETE", f"/saved-jobs/{top_job}", label="unsave job")

        session = call(client, "POST", "/interviews", 201, "create interview (3 questions)",
                       json={"job_id": top_job, "n": 3})
        sid = session["id"]
        qid = session["questions"][0]["id"]
        assert session.get("company"), "create_interview should also return the job's company"
        assert all(q.get("type") for q in session["questions"]), "every question should have a type"
        types_seen = {q["type"] for q in session["questions"]}
        print(f"   question types: {sorted(types_seen)}")
        assert "personalised" in session, "session should report whether questions were personalised"
        # The current resume (third_resume, skills=["accounting"]) has non-empty skills, so this
        # session should be personalised to it.
        assert session["personalised"] is True, "expected personalisation with a non-empty-skills resume"
        print(f"   personalised: {session['personalised']}")

        call(client, "POST", "/interviews/transcribe", 422, "transcribe with no audio content",
             files={"audio": ("empty.wav", b"", "audio/wav")})

        answer = call(client, "POST", f"/interviews/{sid}/answers", label="submit text answer",
                      json={"question_id": qid, "text": "I completed a sales internship and tracked leads in Excel."})
        assert answer["transcribed"] is False
        print(f"   score: {answer['score']}/10")

        call(client, "POST", f"/interviews/{sid}/answers", 422, "empty answer rejected",
             json={"question_id": qid, "text": "   "})

        detail = call(client, "GET", f"/interviews/{sid}", label="get interview")
        answered = [q for q in detail["questions"] if q["answer"]]
        assert all(q.get("type") for q in detail["questions"]), "get_interview should also include type"
        assert detail["personalised"] is True, "get_interview should also include personalised"
        print(f"   answered questions: {len(answered)} of {len(detail['questions'])}")

        call(client, "GET", "/interviews", label="list interviews")

        # --- logout (last: this invalidates the token the rest of the suite relies on) ---
        call(client, "POST", "/auth/logout", label="logout")
        call(client, "GET", "/resumes/latest", 401, "token rejected after logout")
        print("   logout confirmed: token no longer works")
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)

print("\nAll endpoints passed.")
