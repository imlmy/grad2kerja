"""Unit tests for modules.skillgap: a normal match with mixed skill types, a job with no
skills, a job with only soft skills, a resume with no skills, and a mocked LLM failure (no real
API call for that last one -- the OpenAI client is mocked, so explain_gaps's error handling is
tested without spending money or needing network).

Usage: venv/Scripts/python scripts/test_skillgap.py
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import openai

sys.path.append(str(Path(__file__).resolve().parent.parent))
from modules.skillgap import check_skill_match, explain_gaps

failures = 0


def check(label: str, condition: bool) -> None:
    global failures
    print(f"{label:65s} {'ok' if condition else 'FAILED'}")
    if not condition:
        failures += 1


# --- 0. Case/alias normalisation: must not cause a false mismatch ---
print("=== case/alias normalisation ===")
result = check_skill_match(
    resume_skills=["MS Excel"], job_skills=["microsoft excel"],
    resume_languages=["English", "Mandarin "], job_languages=["english", "mandarin"],
)
print(result)
check("'MS Excel' normalises to the canonical term and matches", result["matched"] == ["microsoft excel"])
check("missing is empty once normalised", result["missing"] == [])
check("'English'/'Mandarin ' normalise and both match",
      result["matched_languages"] == ["english", "mandarin"])
check("no missing languages once normalised", result["missing_languages"] == [])
print()

# --- 0b. Proficiency qualifiers must be stripped before alias lookup ---
print("=== qualifier stripping ===")
result = check_skill_match(
    resume_skills=["Python (Advanced)"], job_skills=["python"],
    resume_languages=["English (Fluent)", "Mandarin: Intermediate"],
    job_languages=["english", "mandarin", "bahasa malaysia"],
)
print(result)
check("'Python (Advanced)' still matches 'python'", result["matched"] == ["python"])
check("'English (Fluent)' matches 'english'", "english" in result["matched_languages"])
check("'Mandarin: Intermediate' matches 'mandarin'", "mandarin" in result["matched_languages"])
check("'bahasa malaysia' still reported missing", result["missing_languages"] == ["bahasa malaysia"])

result = check_skill_match(
    resume_skills=[], job_skills=[], resume_languages=["English - Native"], job_languages=["english"],
)
check("'English - Native' matches 'english'", result["matched_languages"] == ["english"])
print()

# --- 1. Normal match, mixed skill types: soft skills must not affect match_pct ---
print("=== normal match (soft skills excluded from match_pct) ===")
result = check_skill_match(
    resume_skills=["python", "communication skills"],
    job_skills=["python", "microsoft excel", "teamwork"],
    resume_languages=["english", "mandarin"],
    job_languages=["english"],
)
print(result)
check("matched excludes soft skills", result["matched"] == ["python"])
check("missing excludes soft skills", result["missing"] == ["microsoft excel"])
check("match_pct is over non-soft skills only (1/2)", result["match_pct"] == 50.0)
check("matched_languages correct", result["matched_languages"] == ["english"])
check("missing_languages empty", result["missing_languages"] == [])
check("soft_skills_required lists the job's soft skills", result["soft_skills_required"] == ["teamwork"])
check("soft_skills_listed is empty (resume has a different soft skill)",
      result["soft_skills_listed"] == [])
check("matched_by_type groups by software/technical",
      result["matched_by_type"] == {"software": [], "technical": ["python"]})
check("missing_by_type groups by software/technical",
      result["missing_by_type"] == {"software": ["microsoft excel"], "technical": []})
check("no message on a normal match", result["message"] is None)
check("unrecognised_terms not part of the result", "unrecognised_terms" not in result)
print()

# --- 2. Job with no skills at all: must not raise ---
print("=== job with no skills ===")
result = check_skill_match(
    resume_skills=["python"], job_skills=[], resume_languages=["english"], job_languages=["english"],
)
print(result)
check("match_pct is None, not an error", result["match_pct"] is None)
check("matched/missing empty", result["matched"] == [] and result["missing"] == [])
check("message set", "doesn't list specific skills" in (result["message"] or ""))
check("language comparison still included", result["matched_languages"] == ["english"])
check("no soft skills required", result["soft_skills_required"] == [])
print()

# --- 3. Job with only soft skills: match_pct must be None, not an error ---
print("=== job with only soft skills ===")
result = check_skill_match(resume_skills=["python"], job_skills=["teamwork", "negotiation"])
print(result)
check("match_pct is None when the job has no non-soft skills", result["match_pct"] is None)
check("matched/missing empty (nothing non-soft to compare)",
      result["matched"] == [] and result["missing"] == [])
check("soft_skills_required lists both soft skills", result["soft_skills_required"] == ["negotiation", "teamwork"])
check("message explains the skills are all soft, not missing from the dictionary",
      "soft skills" in (result["message"] or "").lower())
print()

# --- 4. Resume with no skills ---
print("=== resume with no skills ===")
result = check_skill_match(
    resume_skills=[], job_skills=["python", "sql"], resume_languages=[], job_languages=["english"],
)
print(result)
check("match_pct is 0.0", result["match_pct"] == 0.0)
check("missing is all job skills", result["missing"] == ["python", "sql"])
check("message set", "No skills were found" in (result["message"] or ""))
check("missing_languages is all job languages", result["missing_languages"] == ["english"])
check("missing_by_type groups the missing skills",
      result["missing_by_type"] == {"software": [], "technical": ["python", "sql"]})
print()

# --- 5. Mocked LLM failure ---
print("=== mocked LLM failure ===")
with patch("modules.skillgap.OpenAI") as mock_openai_cls:
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = openai.APIError("simulated failure", object(), body=None)
    mock_openai_cls.return_value = mock_client
    try:
        explain_gaps(["python"], ["sql"], "Backend Developer")
        check("raises RuntimeError on API failure", False)
    except RuntimeError as e:
        check("raises RuntimeError on API failure", True)
        check("message doesn't leak the raw exception text", "simulated failure" not in str(e))
    mock_client.chat.completions.create.assert_called_once()
    _, kwargs = mock_client.chat.completions.create.call_args
    check("timeout=20 was passed to the API call", kwargs.get("timeout") == 20)
print()

# --- 6. Mocked: explain_gaps returns structured JSON and separates soft skills from missing ---
print("=== mocked: explain_gaps returns structured JSON, separates soft skills ===")
with patch("modules.skillgap.OpenAI") as mock_openai_cls:
    client = MagicMock()
    message = MagicMock()
    message.content = json.dumps({
        "summary": "Your Python experience is directly relevant.",
        "missing": [{"skill": "sql", "why": "Used to query data.", "learn": "Official documentation"}],
        "soft_skills": "Teamwork is best demonstrated through experience and interview practice.",
    })
    client.chat.completions.create.return_value.choices = [MagicMock(message=message)]
    mock_openai_cls.return_value = client
    result = explain_gaps(["python"], ["sql"], "Backend Developer", soft_skills=["teamwork"])
    _, kwargs = client.chat.completions.create.call_args
    prompt = kwargs["messages"][0]["content"]
    check("prompt speaks to the user directly as 'you'",
          "you already have" in prompt.lower() and "they already have" not in prompt.lower())
    check("prompt mentions the soft skill", "teamwork" in prompt.lower())
    check("prompt frames soft skills as qualities to demonstrate, not studied",
          "demonstrat" in prompt.lower())
    check("prompt requests JSON only", "json" in prompt.lower())
    check("response_format requests a JSON object", kwargs.get("response_format") == {"type": "json_object"})
    check("result has the model's summary", result["summary"] == "Your Python experience is directly relevant.")
    check("result has the missing-skill breakdown",
          result["missing"] == [{"skill": "sql", "why": "Used to query data.", "learn": "Official documentation"}])
    check("result carries the soft_skills note",
          result["soft_skills"] == "Teamwork is best demonstrated through experience and interview practice.")

    client.reset_mock()
    message_no_soft = MagicMock()
    message_no_soft.content = json.dumps({
        "summary": "Your Python experience is directly relevant.",
        "missing": [{"skill": "sql", "why": "Used to query data.", "learn": "Official documentation"}],
    })
    client.chat.completions.create.return_value.choices = [MagicMock(message=message_no_soft)]
    result_no_soft = explain_gaps(["python"], ["sql"], "Backend Developer", soft_skills=None)
    _, kwargs = client.chat.completions.create.call_args
    prompt_no_soft = kwargs["messages"][0]["content"]
    check("no soft_skills given -> no soft-skills mention in the prompt",
          "soft skill" not in prompt_no_soft.lower())
    check("no soft_skills key in the result when not requested", "soft_skills" not in result_no_soft)
print()

# --- 7. Mocked: invalid JSON is retried once, then raises RuntimeError ---
print("=== mocked: invalid JSON retried once, then RuntimeError ===")
with patch("modules.skillgap.OpenAI") as mock_openai_cls:
    client = MagicMock()
    bad_message = MagicMock()
    bad_message.content = "not valid json"
    client.chat.completions.create.return_value.choices = [MagicMock(message=bad_message)]
    mock_openai_cls.return_value = client
    try:
        explain_gaps(["python"], ["sql"], "Backend Developer")
        check("raises RuntimeError when the JSON is still invalid after one retry", False)
    except RuntimeError:
        check("raises RuntimeError when the JSON is still invalid after one retry", True)
    check("retried exactly once (2 calls total)", client.chat.completions.create.call_count == 2)
print()

# --- 8. Mocked: a missing-skill item the model invented is dropped, not kept ---
print("=== mocked: hallucinated skill not in `missing` is dropped ===")
with patch("modules.skillgap.OpenAI") as mock_openai_cls:
    client = MagicMock()
    message = MagicMock()
    message.content = json.dumps({
        "summary": "Good relevant skills.",
        "missing": [
            {"skill": "sql", "why": "Needed for queries.", "learn": "Official documentation"},
            {"skill": "excel", "why": "Not actually required for this role.", "learn": "Free online course"},
        ],
    })
    client.chat.completions.create.return_value.choices = [MagicMock(message=message)]
    mock_openai_cls.return_value = client
    result = explain_gaps(["python"], ["sql"], "Backend Developer")
    check("hallucinated 'excel' item (not in `missing`) is dropped", result["missing"] == [
        {"skill": "sql", "why": "Needed for queries.", "learn": "Official documentation"},
    ])
print()

# --- 9. No missing skills -> None, no API call made ---
print("=== no missing skills -> None, no API call ===")
with patch("modules.skillgap.OpenAI") as mock_openai_cls:
    result = explain_gaps(["python"], [], "Backend Developer")
    check("returns None when there are no missing skills", result is None)
    check("no API call made", not mock_openai_cls.called)
print()

if failures:
    sys.exit(f"{failures} check(s) failed.")
print("All checks passed.")
