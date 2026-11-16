"""Check Skill Match: compare a resume's skills and languages with a job's."""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import APIError, AuthenticationError, OpenAI

from modules.skill_dictionary import ALIASES, LANGUAGE_ALIASES, normalise_terms, skill_type

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

    Both sides are normalised (stripped, lowercased, aliased to the canonical term) before
    comparing, so case/whitespace/wording differences (e.g. "English " vs "english", "MS Excel"
    vs "microsoft excel") never cause a false mismatch. Returned terms are the canonical,
    lowercase form.
    """
    resume_skills = normalise_terms(resume_skills, ALIASES)
    job_skills = normalise_terms(job_skills, ALIASES)
    resume_languages = normalise_terms(resume_languages, LANGUAGE_ALIASES)
    job_languages = normalise_terms(job_languages, LANGUAGE_ALIASES)

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


def _clean_explanation(data: object, missing: list[str]) -> dict | None:
    """Validate the model's parsed JSON reply. Returns the cleaned {"summary", "missing"} dict,
    or None if the shape is invalid (caller retries once, then raises RuntimeError). An item
    whose "skill" isn't in `missing` is dropped rather than invalidating the whole reply -- the
    model naming an extra or misspelled skill shouldn't lose the rest of a good explanation."""
    if not isinstance(data, dict):
        return None
    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return None
    raw_missing = data.get("missing")
    if not isinstance(raw_missing, list):
        return None
    missing_set = set(missing)
    cleaned_missing = []
    for item in raw_missing:
        if not isinstance(item, dict):
            return None
        skill, why, learn = item.get("skill"), item.get("why"), item.get("learn")
        if not all(isinstance(v, str) and v.strip() for v in (skill, why, learn)):
            return None
        if skill in missing_set:
            cleaned_missing.append({"skill": skill.strip(), "why": why.strip(), "learn": learn.strip()})
    return {"summary": summary.strip(), "missing": cleaned_missing}


def explain_gaps(matched: list[str], missing: list[str], job_title: str,
                  soft_skills: list[str] | None = None) -> dict | None:
    """Ask the LLM to explain why the matched skills are relevant and, for each missing skill,
    why it matters for the role and the TYPE of free resource to learn it (not specific course
    names or URLs, which go stale and can't be verified here). Speaks to the user directly as
    "you", not "they" or "the candidate".

    soft_skills, if given, are the role's required soft skills -- described in the result as
    qualities to demonstrate through experience and in the mock interview, never as something
    "missing" to study (unlike the software/technical skills in `missing`).

    Returns None if there are no missing skills (nothing to explain). Otherwise a dict:
    {"summary": str, "missing": [{"skill": str, "why": str, "learn": str}, ...], "soft_skills":
    str} -- "soft_skills" is present only when `soft_skills` was given and the model included it.

    The model is read from OPENAI_MODEL in .env (default gpt-4o-mini) and asked for JSON only.
    Raises RuntimeError if OPENAI_API_KEY is missing, the API call fails, or the model's JSON
    reply is still invalid after one retry (same retry pattern as modules.interview._ask_json).
    """
    if not missing:
        return None

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env to use skill gap explanations.")

    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    client = OpenAI(api_key=api_key)
    have_part = f"You already have: {', '.join(matched)}." if matched else (
        "You don't yet have any of the skills this role lists."
    )
    soft_instruction = (
        f' Also include a "soft_skills" field: one sentence noting that '
        f'{", ".join(soft_skills)} are best demonstrated through experience and interview '
        "practice, not studied like the missing skills above."
        if soft_skills else ""
    )
    prompt = (
        f"You are a fresh graduate applying for the job '{job_title}'. {have_part} You are "
        f"missing: {', '.join(missing)}. Speak to the user directly as \"you\" throughout, never "
        'in the third person. Reply with JSON only in this exact form: {"summary": "<one sentence '
        'on why the skills you already have are relevant>", "missing": [{"skill": "<exact '
        'missing skill name>", "why": "<one short sentence, at most 20 words, on why it matters '
        'for this role>", "learn": "<type of free resource, e.g. Official documentation, Free '
        'online course, Video tutorials, Practice project>"}, ...]}' + soft_instruction +
        " Do not name specific course titles, providers or URLs."
    )

    for _ in range(2):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                timeout=EXPLAIN_TIMEOUT,
            )
        except AuthenticationError as e:
            raise RuntimeError("OpenAI rejected OPENAI_API_KEY (invalid or revoked). Check .env.") from e
        except APIError as e:
            raise RuntimeError(f"OpenAI request failed ({type(e).__name__}). Try again later.") from e
        try:
            raw = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            continue
        cleaned = _clean_explanation(raw, missing)
        if cleaned is None:
            continue
        if soft_skills:
            soft_text = raw.get("soft_skills") if isinstance(raw, dict) else None
            if isinstance(soft_text, str) and soft_text.strip():
                cleaned["soft_skills"] = soft_text.strip()
        return cleaned
    raise RuntimeError("The model did not return a valid explanation after retrying.")
