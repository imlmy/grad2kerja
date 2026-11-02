"""Check Skill Match: compare a resume's skills and languages with a job's."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import APIError, AuthenticationError, OpenAI

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

DEFAULT_MODEL = "gpt-4o-mini"
EXPLAIN_TIMEOUT = 20


def check_skill_match(
    resume_skills: list[str],
    job_skills: list[str],
    resume_languages: list[str] | None = None,
    job_languages: list[str] | None = None,
) -> dict:
    """Compare a resume against one job's skills and languages.

    Languages are reported separately (matched_languages/missing_languages) and never counted in
    match_pct, which reflects skills only. If the job lists no skills, match_pct is None rather
    than raising -- the posting just doesn't have anything to compare against, which is a data
    gap, not an input error. If the resume has no skills, match_pct is 0.0 with a message.
    unrecognised_terms is intentionally not part of this function -- it's internal-only, for
    future manual dictionary review, not something to compare against a job.
    """
    job_lang_set = set(job_languages or [])
    resume_lang_set = set(resume_languages or [])
    matched_languages = sorted(resume_lang_set & job_lang_set)
    missing_languages = sorted(job_lang_set - resume_lang_set)

    if not job_skills:
        return {
            "matched": [],
            "missing": [],
            "match_pct": None,
            "matched_languages": matched_languages,
            "missing_languages": missing_languages,
            "message": "This posting doesn't list specific skills we can recognise.",
        }

    job_set = set(job_skills)

    if not resume_skills:
        return {
            "matched": [],
            "missing": sorted(job_set),
            "match_pct": 0.0,
            "matched_languages": matched_languages,
            "missing_languages": missing_languages,
            "message": "No skills were found in this resume, so no skills could be matched to the job.",
        }

    matched = sorted(job_set & set(resume_skills))
    missing = sorted(job_set - set(resume_skills))
    return {
        "matched": matched,
        "missing": missing,
        "match_pct": round(100 * len(matched) / len(job_set), 1),
        "matched_languages": matched_languages,
        "missing_languages": missing_languages,
        "message": None,
    }


def explain_gaps(matched: list[str], missing: list[str], job_title: str) -> str:
    """Ask the LLM to explain why the matched skills are relevant and what the missing ones are
    for, with the TYPE of free resource to learn each missing one (not specific course names or
    URLs, which go stale and can't be verified here).

    The model is read from OPENAI_MODEL in .env (default gpt-4o-mini). Returns plain text.
    """
    if not missing:
        return "No missing skills, so there is nothing to explain."

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env to use skill gap explanations.")

    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    have_part = f"They already have: {', '.join(matched)}." if matched else (
        "They don't yet have any of the skills this role lists."
    )
    prompt = (
        f"A fresh graduate is applying for the job '{job_title}'. {have_part} "
        f"They are missing: {', '.join(missing)}. In at most 150 words: briefly explain why the "
        "skills they already have are relevant to this role, then explain why each missing skill "
        "matters for it, and suggest the TYPE of free resource to learn each missing skill (e.g. "
        "official documentation, a free online course, video tutorials, a practice project) -- "
        "do not name specific course titles, providers or URLs."
    )
    try:
        response = OpenAI(api_key=api_key).chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            timeout=EXPLAIN_TIMEOUT,
        )
    except AuthenticationError as e:
        raise RuntimeError("OpenAI rejected OPENAI_API_KEY (invalid or revoked). Check .env.") from e
    except APIError as e:
        raise RuntimeError(f"OpenAI request failed ({type(e).__name__}). Try again later.") from e
    return response.choices[0].message.content.strip()
