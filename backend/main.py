"""FastAPI app: wires the modules to SQLite. Run from the project root:
    venv/Scripts/uvicorn backend.main:app --reload
"""
import json
import re
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from backend.database import db, init_db  # noqa: E402
from backend.schemas import (  # noqa: E402
    AnswerSubmit, InterviewCreate, LoginRequest, ProfileUpdate,
    RecommendRequest, RegisterRequest, ResumeUpdate, SavedJobRequest, SkillGapRequest,
)
from modules.auth import generate_token, hash_password, verify_password  # noqa: E402
from modules.interview import evaluate_answer, generate_questions, transcribe  # noqa: E402
from modules.matching import match_job, preload_model, recommend_jobs  # noqa: E402
from modules.resume_parser import parse_resume  # noqa: E402
from modules.skillgap import check_skill_match, explain_gaps  # noqa: E402

_jobs = pd.read_csv(ROOT / "data" / "jobs_entry_skills.csv")
for _col in ("job_title", "company", "location", "category", "subcategory", "type", "salary",
             "listingDate", "skills", "languages", "descriptions", "description_display"):
    _jobs[_col] = _jobs[_col].fillna("")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    preload_model()  # so the first /recommendations call doesn't pay the model-load cost
    yield


app = FastAPI(title="Grad2Kerja", lifespan=lifespan)


@app.exception_handler(RuntimeError)
async def _service_error(request, exc: RuntimeError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def _input_error(request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(RequestValidationError)
async def _validation_error(request, exc: RequestValidationError):
    """FastAPI's default body for a pydantic validation failure is a list of {loc, msg, type}
    dicts -- fine for API clients, unreadable if shown to a person. Return just the first error's
    message instead, as a single string, matching the other 422 handlers above. Pydantic v2
    prefixes a field_validator's own ValueError message with "Value error, "; strip that so e.g.
    "Enter a valid email address." doesn't become "Value error, Enter a valid email address."."""
    msg = exc.errors()[0].get("msg", "Invalid input.")
    prefix = "Value error, "
    if msg.startswith(prefix):
        msg = msg[len(prefix):]
    return JSONResponse(status_code=422, content={"detail": msg})


def _bearer_token(authorization: str | None) -> str:
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Not logged in.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(401, "Not logged in.")
    return token


def current_user_id(authorization: str | None = Header(None)) -> int:
    """Every endpoint below (other than /auth/register and /auth/login) requires an
    "Authorization: Bearer <token>" header, with the token returned by /auth/login. The token
    maps to a user via the sessions table -- /auth/logout deletes the row to end the session."""
    token = _bearer_token(authorization)
    with db() as conn:
        row = conn.execute("SELECT user_id FROM sessions WHERE token = ?", (token,)).fetchone()
    if row is None:
        raise HTTPException(401, "Invalid or expired session. Please log in again.")
    return row["user_id"]


# --- authentication ---

@app.post("/auth/register", status_code=201)
def register(req: RegisterRequest) -> dict:
    """UC001 1.1.7-1.1.8: no session is created here -- the frontend shows a success message and
    sends the candidate to log in separately, rather than signing them in automatically."""
    with db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (req.email,)).fetchone()
        if existing is not None:
            raise HTTPException(409, "An account with this email already exists.")
        user_id = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (req.name.strip(), req.email, hash_password(req.password)),
        ).lastrowid
    return {"id": user_id, "name": req.name.strip(), "email": req.email}


@app.post("/auth/login")
def login(req: LoginRequest) -> dict:
    with db() as conn:
        row = conn.execute(
            "SELECT id, name, password_hash FROM users WHERE email = ?", (req.email,)
        ).fetchone()
        if row is None or not row["password_hash"] or not verify_password(req.password, row["password_hash"]):
            raise HTTPException(401, "Incorrect email or password.")
        token = generate_token()
        conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, row["id"]))
    return {"token": token, "id": row["id"], "name": row["name"], "email": req.email}


@app.post("/auth/logout")
def logout(authorization: str | None = Header(None), user_id: int = Depends(current_user_id)) -> dict:
    token = _bearer_token(authorization)
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    return {"logged_out": True}


# --- profile ---

def _profile_json(row) -> dict:
    return {"id": row["id"], "name": row["name"], "email": row["email"],
            "field_of_study": row["field_of_study"], "location": row["location"]}


@app.get("/profile")
def get_profile(user_id: int = Depends(current_user_id)) -> dict:
    with db() as conn:
        row = conn.execute(
            "SELECT id, name, email, field_of_study, location FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return _profile_json(row)


@app.patch("/profile")
def update_profile(req: ProfileUpdate, user_id: int = Depends(current_user_id)) -> dict:
    """Name, field of study and location only -- email has no change-email flow, so it's never
    accepted here (UC002: shown read-only in the UI)."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise ValueError("Nothing to update.")
    with db() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", (*updates.values(), user_id))
        row = conn.execute(
            "SELECT id, name, email, field_of_study, location FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return _profile_json(row)


def _find_job(job_id: int) -> pd.Series | None:
    rows = _jobs[_jobs["job_id"] == job_id]
    return rows.iloc[0] if len(rows) else None


def _job_or_404(job_id: int) -> pd.Series:
    job = _find_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job


def _split(value: str) -> list[str]:
    return [s for s in str(value).split("; ") if s]


def _truncate_at_word(text: str, limit: int = 220) -> str:
    """Cut text to at most `limit` characters, breaking at the last word boundary rather than
    mid-word, and mark the cut with "…"."""
    text = str(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_space = cut.rfind(" ")
    if last_space > 0:
        cut = cut[:last_space]
    return cut.rstrip() + "…"


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _card_summary(text: str, limit: int = 200) -> str:
    """The first 1-2 sentences of a job description, for a job card preview -- capped at
    `limit` characters and cut at a word boundary (not mid-sentence or mid-word)."""
    sentences = _SENTENCE_SPLIT.split(str(text).strip())
    if not sentences:
        return ""
    summary = sentences[0]
    if len(sentences) > 1:
        with_second = f"{summary} {sentences[1]}"
        if len(with_second) <= limit:
            summary = with_second
    return _truncate_at_word(summary, limit)


def _job_json(job: pd.Series, full: bool = False) -> dict:
    data = {
        "job_id": int(job["job_id"]),
        "title": job["job_title"],
        "company": job["company"],
        "location": job["location"],
        "category": job["category"],
        "type": job["type"],
        "skills": _split(job["skills"]),
        "summary": _card_summary(job["descriptions"]),
    }
    if full:
        data |= {
            "subcategory": job["subcategory"],
            "salary": job["salary"],
            "listing_date": job["listingDate"],
            "languages": _split(job["languages"]),
            "description": job["description_display"] or job["descriptions"],
        }
    return data


def _interview_job(job: pd.Series) -> dict:
    return {"job_title": job["job_title"], "category": job["category"],
            "skills": job["skills"], "description": job["descriptions"]}


def _resume_context(conn, job_skills: list[str], user_id: int) -> dict | None:
    """Build the resume-grounded context for generate_questions from the user's latest resume --
    only skills, projects and job skills missing from the resume. Never name, contact details,
    education or the full resume text. Returns None if the user has no resume yet."""
    row = conn.execute(
        "SELECT skills, projects FROM resumes WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
    ).fetchone()
    if row is None:
        return None
    skills = json.loads(row["skills"])
    projects = json.loads(row["projects"])
    return {"skills": skills, "projects": projects, "missing_skills": sorted(set(job_skills) - set(skills))}


def _resume_or_404(conn, resume_id: int, user_id: int) -> dict:
    row = conn.execute(
        "SELECT * FROM resumes WHERE id = ? AND user_id = ?", (resume_id, user_id)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Resume not found")
    return {
        "id": row["id"],
        "filename": row["filename"],
        "text": row["text"],
        "skills": json.loads(row["skills"]),
        "languages": json.loads(row["languages"]),
        "education": json.loads(row["education"]),
        "experience": json.loads(row["experience"]),
        "projects": json.loads(row["projects"]),
        "unrecognised_terms": json.loads(row["unrecognised_terms"]),
        "size_bytes": row["size_bytes"],
        "created_at": row["created_at"],
    }


# --- resumes ---

def _clear_recommendations(conn, user_id: int) -> None:
    """Drop the user's stored recommendations so the dashboard recomputes from the current
    resume instead of showing matches based on a resume that no longer applies."""
    conn.execute("DELETE FROM recommendations WHERE user_id = ?", (user_id,))


def _clear_skill_matches(conn, user_id: int) -> None:
    """Drop the user's stored skill match results so they get recomputed against the current
    resume instead of showing a match based on a resume that no longer applies."""
    conn.execute("DELETE FROM skill_matches WHERE user_id = ?", (user_id,))


MAX_RESUME_BYTES = 5 * 1024 * 1024


@app.post("/resumes", status_code=201)
def upload_resume(file: UploadFile = File(...), user_id: int = Depends(current_user_id)) -> dict:
    content = file.file.read()
    if not (file.filename or "").lower().endswith(".pdf") or len(content) > MAX_RESUME_BYTES:
        raise ValueError("Only PDF resumes up to 5 MB are supported.")
    parsed = parse_resume(content)
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO resumes (user_id, filename, text, skills, languages, education, "
            "experience, projects, unrecognised_terms, size_bytes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, file.filename or "resume.pdf", parsed["text"], json.dumps(parsed["skills"]),
             json.dumps(parsed["languages"]), json.dumps(parsed["education"]),
             json.dumps(parsed["experience"]), json.dumps(parsed["projects"]),
             json.dumps(parsed["unrecognised_terms"]), len(content)),
        )
        resume_id = cur.lastrowid
        # A new resume replaces the profile recommendations and skill matches were computed from.
        _clear_recommendations(conn, user_id)
        _clear_skill_matches(conn, user_id)
    return {"id": resume_id, "filename": file.filename, "skills": parsed["skills"],
            "languages": parsed["languages"], "education": parsed["education"],
            "experience": parsed["experience"], "projects": parsed["projects"],
            "unrecognised_terms": parsed["unrecognised_terms"], "size_bytes": len(content)}


@app.patch("/resumes/{resume_id}")
def update_resume(resume_id: int, req: ResumeUpdate, user_id: int = Depends(current_user_id)) -> dict:
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise ValueError("Nothing to update.")
    with db() as conn:
        _resume_or_404(conn, resume_id, user_id)
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = [json.dumps(v) for v in updates.values()]
        conn.execute(f"UPDATE resumes SET {set_clause} WHERE id = ?", (*values, resume_id))
        if "skills" in updates:
            # Only skills feed the recommendation embedding (see modules/matching._embed_resume) --
            # editing education/experience/projects/languages alone wouldn't change the matches.
            _clear_recommendations(conn, user_id)
        if "skills" in updates or "languages" in updates:
            # check_skill_match compares both skills and languages.
            _clear_skill_matches(conn, user_id)
        resume = _resume_or_404(conn, resume_id, user_id)
    resume.pop("text")
    return resume


@app.get("/resumes/latest")
def get_latest_resume(user_id: int = Depends(current_user_id)) -> dict:
    with db() as conn:
        row = conn.execute(
            "SELECT id FROM resumes WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(404, "No resume uploaded yet")
        resume = _resume_or_404(conn, row["id"], user_id)
    resume.pop("text")
    return resume


@app.get("/resumes/{resume_id}")
def get_resume(resume_id: int, user_id: int = Depends(current_user_id)) -> dict:
    with db() as conn:
        resume = _resume_or_404(conn, resume_id, user_id)
    resume.pop("text")
    return resume


# --- jobs ---

@app.get("/jobs")
def list_jobs(
    category: str | None = None,
    location: str | None = None,
    job_type: str | None = Query(None, alias="type"),
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(current_user_id),
) -> dict:
    mask = pd.Series(True, index=_jobs.index)
    if category:
        mask &= _jobs["category"].str.lower() == category.lower()
    if location:
        mask &= _jobs["location"].str.lower().str.contains(location.lower(), regex=False)
    if job_type:
        mask &= _jobs["type"].str.lower() == job_type.lower()
    if q:
        ql = q.lower()
        mask &= (
            _jobs["job_title"].str.lower().str.contains(ql, regex=False)
            | _jobs["company"].str.lower().str.contains(ql, regex=False)
            | _jobs["descriptions"].str.lower().str.contains(ql, regex=False)
        )
    page = _jobs[mask].iloc[offset:offset + limit]
    return {"total": int(mask.sum()), "items": [_job_json(job) for _, job in page.iterrows()]}


@app.get("/jobs/options")
def job_options(user_id: int = Depends(current_user_id)) -> dict:
    return {
        "categories": sorted(c for c in _jobs["category"].unique() if c),
        "types": sorted(t for t in _jobs["type"].unique() if t),
    }


@app.get("/jobs/{job_id}")
def get_job(job_id: int, user_id: int = Depends(current_user_id)) -> dict:
    return _job_json(_job_or_404(job_id), full=True)


@app.get("/jobs/{job_id}/match")
def job_match(job_id: int, user_id: int = Depends(current_user_id)) -> dict | None:
    """The user's latest resume vs this one job, via the same embedding/cosine recommend_jobs()
    uses -- a semantic match for the Job Details page, not the skill-only check_skill_match.
    Returns None (not an error) if the user has no resume yet."""
    _job_or_404(job_id)
    with db() as conn:
        row = conn.execute(
            "SELECT id FROM resumes WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
        ).fetchone()
        if row is None:
            return None
        resume = _resume_or_404(conn, row["id"], user_id)
    return match_job(resume, job_id)


@app.post("/recommendations")
def recommend(req: RecommendRequest, user_id: int = Depends(current_user_id)) -> list[dict]:
    with db() as conn:
        resume = _resume_or_404(conn, req.resume_id, user_id)
    filters = {"category": req.category, "location": req.location, "type": req.type}
    df = recommend_jobs(resume, k=req.k, filters=filters)
    results = [
        {"job_id": int(r["job_id"]), "title": r["title"], "company": r["company"],
         "location": r["location"], "category": r["category"], "score": round(float(r["score"]), 4),
         "match_pct": int(r["match_pct"]), "matched_skills": list(r["matched_skills"])}
        for r in df.to_dict("records")
    ]
    # UC011: keep the user's latest UNFILTERED recommendations for the dashboard (replaces the
    # previous batch). A filtered call (e.g. narrowing by location) is a one-off view, not the
    # user's general "best matches", so it isn't stored and doesn't overwrite what is.
    if req.category is None and req.location is None and req.type is None:
        with db() as conn:
            conn.execute("DELETE FROM recommendations WHERE user_id = ?", (user_id,))
            conn.executemany(
                "INSERT INTO recommendations (user_id, job_id, match_pct) VALUES (?, ?, ?)",
                [(user_id, r["job_id"], r["match_pct"]) for r in results],
            )
    return results


@app.get("/recommendations/latest")
def latest_recommendations(user_id: int = Depends(current_user_id)) -> list[dict]:
    """The most recent batch POST /recommendations computed for this user (UC011)."""
    with db() as conn:
        rows = conn.execute(
            "SELECT job_id, match_pct, created_at FROM recommendations WHERE user_id = ? "
            "ORDER BY match_pct DESC",
            (user_id,),
        ).fetchall()
    items = []
    for row in rows:
        job = _find_job(row["job_id"])
        if job is not None:
            items.append({**_job_json(job), "match_pct": row["match_pct"], "created_at": row["created_at"]})
    return items


@app.post("/skill-gap")
def skill_gap(req: SkillGapRequest, user_id: int = Depends(current_user_id)) -> dict:
    with db() as conn:
        resume = _resume_or_404(conn, req.resume_id, user_id)
    job = _job_or_404(req.job_id)
    result = check_skill_match(
        resume["skills"], _split(job["skills"]), resume["languages"], _split(job["languages"]),
    )

    # UC011 step 4: keep this as the user's latest skill match for the dashboard.
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO skill_matches (user_id, job_id, match_pct, matched, missing) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, req.job_id, result["match_pct"], json.dumps(result["matched"]),
             json.dumps(result["missing"])),
        )

    result["explanation"] = None
    if req.explain and result["missing"]:
        try:
            result["explanation"] = explain_gaps(result["matched"], result["missing"], job["job_title"])
        except RuntimeError as e:
            # UC008 alt flow 8.1: the skill match itself is still good, just note the explanation
            # couldn't be generated, instead of losing the whole result.
            result["explanation_note"] = f"Explanation unavailable: {e}"
    return result


@app.get("/skill-gap/latest")
def latest_skill_match(user_id: int = Depends(current_user_id)) -> dict | None:
    """The most recently computed skill match for this user, across any job (UC011 step 4)."""
    with db() as conn:
        row = conn.execute(
            "SELECT job_id, match_pct, matched, missing, created_at FROM skill_matches "
            "WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    job = _find_job(row["job_id"])
    return {
        "job_id": row["job_id"],
        "title": job["job_title"] if job is not None else None,
        "company": job["company"] if job is not None else None,
        "match_pct": row["match_pct"],
        "matched": json.loads(row["matched"]),
        "missing": json.loads(row["missing"]),
        "created_at": row["created_at"],
    }


@app.get("/skill-gap/{job_id}")
def skill_gap_for_job(job_id: int, user_id: int = Depends(current_user_id)) -> dict | None:
    """Skill match for one specific job: the stored skill_matches row if one already exists for
    it, otherwise computed live -- no LLM call, and never written to skill_matches. Used by the
    Job Details "Apply Now" readiness check, which must not change the dashboard's latest skill
    match (that's only ever set by the explicit POST /skill-gap on the Skill Match page).
    Returns None if the user has no resume yet."""
    job = _job_or_404(job_id)
    with db() as conn:
        row = conn.execute(
            "SELECT match_pct, matched, missing FROM skill_matches WHERE user_id = ? AND job_id = ?",
            (user_id, job_id),
        ).fetchone()
        if row is not None:
            return {"match_pct": row["match_pct"], "matched": json.loads(row["matched"]),
                    "missing": json.loads(row["missing"])}
        resume_row = conn.execute(
            "SELECT id FROM resumes WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
        ).fetchone()
        if resume_row is None:
            return None
        resume = _resume_or_404(conn, resume_row["id"], user_id)
    result = check_skill_match(resume["skills"], _split(job["skills"]))
    return {"match_pct": result["match_pct"], "matched": result["matched"], "missing": result["missing"]}


# --- saved jobs ---

@app.post("/saved-jobs", status_code=201)
def save_job(req: SavedJobRequest, user_id: int = Depends(current_user_id)) -> dict:
    _job_or_404(req.job_id)
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO saved_jobs (user_id, job_id) VALUES (?, ?)",
                     (user_id, req.job_id))
    return {"job_id": req.job_id, "saved": True}


@app.get("/saved-jobs")
def list_saved_jobs(user_id: int = Depends(current_user_id)) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT job_id, saved_at FROM saved_jobs WHERE user_id = ? ORDER BY saved_at DESC",
            (user_id,),
        ).fetchall()
    items = []
    for row in rows:
        job = _find_job(row["job_id"])
        if job is not None:
            items.append({**_job_json(job), "saved_at": row["saved_at"]})
    return items


@app.delete("/saved-jobs/{job_id}")
def unsave_job(job_id: int, user_id: int = Depends(current_user_id)) -> dict:
    with db() as conn:
        cur = conn.execute("DELETE FROM saved_jobs WHERE user_id = ? AND job_id = ?", (user_id, job_id))
    if cur.rowcount == 0:
        raise HTTPException(404, "Job is not in your saved list")
    return {"job_id": job_id, "saved": False}


# --- mock interviews ---

@app.post("/interviews", status_code=201)
def create_interview(req: InterviewCreate, user_id: int = Depends(current_user_id)) -> dict:
    job = _job_or_404(req.job_id)
    with db() as conn:
        resume_context = _resume_context(conn, _split(job["skills"]), user_id)
    personalised = bool(resume_context and (resume_context["skills"] or resume_context["projects"]))
    questions = generate_questions(_interview_job(job), resume_context=resume_context, n=req.n)
    with db() as conn:
        session_id = conn.execute(
            "INSERT INTO interview_sessions (user_id, job_id, personalised) VALUES (?, ?, ?)",
            (user_id, req.job_id, int(personalised)),
        ).lastrowid
        rows = []
        for position, q in enumerate(questions, 1):
            question_id = conn.execute(
                "INSERT INTO interview_questions (session_id, position, question, type) VALUES (?, ?, ?, ?)",
                (session_id, position, q["question"], q["type"]),
            ).lastrowid
            rows.append({"id": question_id, "position": position, "question": q["question"], "type": q["type"]})
    return {"id": session_id, "job_id": req.job_id, "job_title": job["job_title"],
            "company": job["company"], "personalised": personalised, "questions": rows}


@app.get("/interviews")
def list_interviews(user_id: int = Depends(current_user_id)) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT s.id, s.job_id, s.personalised, s.created_at, COUNT(q.id) AS total, "
            "COUNT(a.id) AS answered, AVG(a.score) AS avg_score "
            "FROM interview_sessions s "
            "LEFT JOIN interview_questions q ON q.session_id = s.id "
            "LEFT JOIN interview_answers a ON a.question_id = q.id "
            "WHERE s.user_id = ? GROUP BY s.id ORDER BY s.id DESC",
            (user_id,),
        ).fetchall()
    items = []
    for row in rows:
        job = _find_job(row["job_id"])
        items.append({
            "id": row["id"], "job_id": row["job_id"], "personalised": bool(row["personalised"]),
            "job_title": job["job_title"] if job is not None else None,
            "company": job["company"] if job is not None else None,
            "created_at": row["created_at"],
            "total_questions": row["total"], "answered": row["answered"],
            "overall_score": round(row["avg_score"] * 10) if row["answered"] else None,
        })
    return items


@app.get("/interviews/{session_id}")
def get_interview(session_id: int, user_id: int = Depends(current_user_id)) -> dict:
    with db() as conn:
        session = conn.execute(
            "SELECT job_id, personalised, created_at FROM interview_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if session is None:
            raise HTTPException(404, "Interview not found")
        rows = conn.execute(
            "SELECT q.id, q.position, q.question, q.type, a.answer, a.transcribed, a.score, "
            "a.strengths, a.improvements "
            "FROM interview_questions q LEFT JOIN interview_answers a ON a.question_id = q.id "
            "WHERE q.session_id = ? ORDER BY q.position",
            (session_id,),
        ).fetchall()
    questions = [
        {"id": r["id"], "position": r["position"], "question": r["question"], "type": r["type"],
         "answer": None if r["answer"] is None else {
             "text": r["answer"], "transcribed": bool(r["transcribed"]), "score": r["score"],
             "strengths": r["strengths"], "improvements": r["improvements"]}}
        for r in rows
    ]
    answered = [q["answer"]["score"] for q in questions if q["answer"]]
    job = _find_job(session["job_id"])
    return {"id": session_id, "job_id": session["job_id"], "personalised": bool(session["personalised"]),
            "job_title": job["job_title"] if job is not None else None,
            "company": job["company"] if job is not None else None,
            "created_at": session["created_at"],
            "overall_score": round(sum(answered) / len(answered) * 10) if answered else None,
            "questions": questions}


@app.post("/interviews/transcribe")
def transcribe_recording(audio: UploadFile = File(...), user_id: int = Depends(current_user_id)) -> dict:
    """Transcribe a recording on its own, so the frontend can show it for review before the
    candidate submits -- not part of submit_answer, which only ever takes text."""
    text = transcribe(audio.file.read(), audio.filename or "answer.webm")
    return {"text": text}


@app.post("/interviews/{session_id}/answers")
def submit_answer(session_id: int, req: AnswerSubmit, user_id: int = Depends(current_user_id)) -> dict:
    with db() as conn:
        session = conn.execute(
            "SELECT job_id FROM interview_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if session is None:
            raise HTTPException(404, "Interview not found")
        question = conn.execute(
            "SELECT question FROM interview_questions WHERE id = ? AND session_id = ?",
            (req.question_id, session_id),
        ).fetchone()
    if question is None:
        raise HTTPException(404, "Question not found in this interview")

    answer_text = req.text.strip()
    if not answer_text:
        raise ValueError("The answer is empty.")

    job = _job_or_404(session["job_id"])
    evaluation = evaluate_answer(question["question"], answer_text, _interview_job(job))

    with db() as conn:
        conn.execute("DELETE FROM interview_answers WHERE question_id = ?", (req.question_id,))
        conn.execute(
            "INSERT INTO interview_answers (question_id, answer, transcribed, score, strengths, improvements) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (req.question_id, answer_text, int(req.transcribed), evaluation["score"],
             evaluation["strengths"], evaluation["improvements"]),
        )
    return {"question_id": req.question_id, "answer": answer_text, "transcribed": req.transcribed, **evaluation}
