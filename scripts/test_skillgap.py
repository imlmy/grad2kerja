"""Unit tests for modules.skillgap: a normal match with mixed skill types, a job with no
skills, a job with only soft skills, a resume with no skills, and a mocked LLM failure (no real
API call for that last one -- the OpenAI client is mocked, so explain_gaps's error handling is
tested without spending money or needing network).

Usage: venv/Scripts/python scripts/test_skillgap.py
"""
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

# --- 6. Mocked: explain_gaps describes soft skills as qualities to demonstrate, not missing ---
print("=== mocked: explain_gaps separates soft skills from missing skills ===")
with patch("modules.skillgap.OpenAI") as mock_openai_cls:
    client = MagicMock()
    message = MagicMock()
    message.content = "Explanation text."
    client.chat.completions.create.return_value.choices = [MagicMock(message=message)]
    mock_openai_cls.return_value = client
    explain_gaps(["python"], ["sql"], "Backend Developer", soft_skills=["teamwork"])
    _, kwargs = client.chat.completions.create.call_args
    prompt = kwargs["messages"][0]["content"]
    check("prompt mentions the soft skill", "teamwork" in prompt.lower())
    check("prompt frames soft skills as qualities to demonstrate, not studied",
          "demonstrat" in prompt.lower())

    client.reset_mock()
    explain_gaps(["python"], ["sql"], "Backend Developer", soft_skills=None)
    _, kwargs = client.chat.completions.create.call_args
    prompt_no_soft = kwargs["messages"][0]["content"]
    check("no soft_skills given -> no soft-skills mention in the prompt",
          "soft skill" not in prompt_no_soft.lower())
print()

if failures:
    sys.exit(f"{failures} check(s) failed.")
print("All checks passed.")
