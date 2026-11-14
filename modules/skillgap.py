"""Check Skill Match: compare a resume's skills and languages with a job's."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import APIError, AuthenticationError, OpenAI

from modules.skill_dictionary import skill_type

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

    Soft skills (skill_type(skill) == "soft") are reported separately via soft_skills_required /
    soft_skills_listed and never count toward matched/missing/match_pct -- resumes usually show
    them through experience rather than listing them, so penalising their absence would be
    misleading. matched_by_type/missing_by_type group the remaining (software/technical) skills
    for display.

    Languages are reported separately (matched_languages/missing_languages) and never counted in
    match_pct either. If the job has no non-soft skills, match_pct is None rather than raising --
    the posting just doesn't have anything to compare against, which is a data gap, not an input
    error. If the resume has no skills at all, match_pct is 0.0 with a message.
    unrecognised_terms is intentionally not part of this function -- it's internal-only, for
    future manual dictionary review, not something to compare against a job.
    """
    job_lang_set = set(job_languages or [])
    resume_lang_set = set(resume_languages or [])
    matched_languages = sorted(resume_lang_set & job_lang_set)
    missing_languages = sorted(job_lang_set - resume_lang_set)

    job_soft = {s for s in (job_skills or []) if skill_type(s) == "soft"}
    resume_soft = {s for s in (resume_skills or []) if skill_type(s) == "soft"}
    soft_skills_required = sorted(job_soft)
    soft_skills_listed = sorted(job_soft & resume_soft)

    def _by_type(skills) -> dict[str, list[str]]:
        skills = set(skills)
        return {
            "software": sorted(s for s in skills if skill_type(s) == "software"),
            "technical": sorted(s for s in skills if skill_type(s) == "technical"),
        }

    job_non_soft = {s for s in (job_skills or []) if skill_type(s) != "soft"}

    if not job_non_soft:
        message = (
            "This posting's required skills are all soft skills, shown separately below."
            if job_skills else "This posting doesn't list specific skills we can recognise."
        )
        return {
            "matched": [],
            "missing": [],
            "match_pct": None,
            "matched_languages": matched_languages,
            "missing_languages": missing_languages,
            "soft_skills_required": soft_skills_required,
            "soft_skills_listed": soft_skills_listed,
            "matched_by_type": _by_type([]),
            "missing_by_type": _by_type([]),
            "message": message,
        }

    if not resume_skills:
        return {
            "matched": [],
            "missing": sorted(job_non_soft),
            "match_pct": 0.0,
            "matched_languages": matched_languages,
            "missing_languages": missing_languages,
            "soft_skills_required": soft_skills_required,
            "soft_skills_listed": soft_skills_listed,
            "matched_by_type": _by_type([]),
            "missing_by_type": _by_type(job_non_soft),
            "message": "No skills were found in this resume, so no skills could be matched to the job.",
        }

    matched_set = job_non_soft & set(resume_skills)
    missing_set = job_non_soft - set(resume_skills)
    return {
        "matched": sorted(matched_set),
        "missing": sorted(missing_set),
        "match_pct": round(100 * len(matched_set) / len(job_non_soft), 1),
        "matched_languages": matched_languages,
        "missing_languages": missing_languages,
        "soft_skills_required": soft_skills_required,
        "soft_skills_listed": soft_skills_listed,
        "matched_by_type": _by_type(matched_set),
        "missing_by_type": _by_type(missing_set),
        "message": None,
    }


def explain_gaps(matched: list[str], missing: list[str], job_title: str,
                  soft_skills: list[str] | None = None) -> str:
    """Ask the LLM to explain why the matched skills are relevant and what the missing ones are
    for, with the TYPE of free resource to learn each missing one (not specific course names or
    URLs, which go stale and can't be verified here).

    soft_skills, if given, are the role's required soft skills -- described as qualities to
    demonstrate through experience and in the mock interview, never as something "missing" to
    study (unlike the software/technical skills in `missing`).

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
    soft_part = (
        f" This role also values these soft skills: {', '.join(soft_skills)}. Briefly note they "
        "are best demonstrated through experience and interview practice, not studied like the "
        "missing skills above."
        if soft_skills else ""
    )
    prompt = (
        f"A fresh graduate is applying for the job '{job_title}'. {have_part} "
        f"They are missing: {', '.join(missing)}.{soft_part} In at most 150 words: briefly explain "
        "why the skills they already have are relevant to this role, then explain why each missing "
        "skill matters for it, and suggest the TYPE of free resource to learn each missing skill "
        "(e.g. official documentation, a free online course, video tutorials, a practice project) -- "
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
