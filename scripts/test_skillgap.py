"""Unit tests for modules.skillgap: a normal match, a job with no skills, a resume with no
skills, and a mocked LLM failure (no real API call for that last one -- the OpenAI client is
mocked, so explain_gaps's error handling is tested without spending money or needing network).

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
    print(f"{label:60s} {'ok' if condition else 'FAILED'}")
    if not condition:
        failures += 1


# --- 1. Normal match ---
print("=== normal match ===")
result = check_skill_match(
    resume_skills=["python", "sql", "communication skills"],
    job_skills=["python", "sql", "teamwork"],
    resume_languages=["english", "mandarin"],
    job_languages=["english"],
)
print(result)
check("matched skills correct", result["matched"] == ["python", "sql"])
check("missing skills correct", result["missing"] == ["teamwork"])
check("match_pct correct (2/3)", result["match_pct"] == 66.7)
check("matched_languages correct", result["matched_languages"] == ["english"])
check("missing_languages empty", result["missing_languages"] == [])
check("no message on a normal match", result["message"] is None)
check("unrecognised_terms not part of the result", "unrecognised_terms" not in result)
print()

# --- 2. Job with no skills: must not raise ---
print("=== job with no skills ===")
result = check_skill_match(
    resume_skills=["python"], job_skills=[], resume_languages=["english"], job_languages=["english"],
)
print(result)
check("match_pct is None, not an error", result["match_pct"] is None)
check("matched/missing empty", result["matched"] == [] and result["missing"] == [])
check("message set", "doesn't list specific skills" in (result["message"] or ""))
check("language comparison still included", result["matched_languages"] == ["english"])
print()

# --- 3. Resume with no skills ---
print("=== resume with no skills ===")
result = check_skill_match(
    resume_skills=[], job_skills=["python", "sql"], resume_languages=[], job_languages=["english"],
)
print(result)
check("match_pct is 0.0", result["match_pct"] == 0.0)
check("missing is all job skills", result["missing"] == ["python", "sql"])
check("message set", "No skills were found" in (result["message"] or ""))
check("missing_languages is all job languages", result["missing_languages"] == ["english"])
print()

# --- 4. Mocked LLM failure ---
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

if failures:
    sys.exit(f"{failures} check(s) failed.")
print("All checks passed.")
