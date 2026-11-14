"""Quick test of modules.resume_parser._parse_text against sample resume text (no PDF needed).

Covers: a skills list using "Excel" (alias match), a fuzzy near-miss ("accounting principle"),
and a resume with no dictionary skills at all -- should return empty lists, not raise.

Usage: venv/Scripts/python scripts/test_resume_sections.py
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from modules.resume_parser import _parse_text

SAMPLES = {
    "skills list with 'Excel'": """
Jane Tan
EDUCATION
Bachelor of Accounting, Universiti Malaya, 2024

SKILLS
Excel, Data Entry, Communication Skills

EXPERIENCE
Accounts Intern, ABC Sdn Bhd
- Prepared journal entries and supported month-end closing.

PROJECTS
Final year project on small business bookkeeping automation.
""",
    "fuzzy near-miss ('accounting principle')": """
Ali Hassan
SKILLS
Accounting principle, Audit, Bookkeeping
""",
    "fuzzy near-miss with leading qualifier ('strong accounting principle')": """
Ali Hassan
Applied strong accounting principle throughout a semester-long audit simulation.
""",
    "no dictionary skills": """
Sam Lee
I enjoy long walks, reading novels, and spending time with family on weekends.
""",
}

for label, text in SAMPLES.items():
    result = _parse_text(text.strip())
    print(f"=== {label} ===")
    print("skills:", result["skills"])
    print("languages:", result["languages"])
    print("unrecognised_terms:", result["unrecognised_terms"])
    print("education:", result["education"])
    print("experience:", result["experience"])
    print("projects:", result["projects"])
    print()

# --- Back-to-back entries with no blank line between them, as real PDF text extraction often
# produces: each project's title+date line must start a new entry (2 entries, not 1). ---
print("=== two projects back-to-back, no blank line between them ===")
BACK_TO_BACK_PROJECTS = """
Jane Tan
PROJECTS
Grad2Kerja - AI Job-Matching & Interview Prep Platform | FYP Jun 2026 - Dec 2026
Built an AI-powered platform for fresh graduates to match jobs, check skill gaps and practise
mock interviews.
Python, Streamlit, FastAPI, spaCy, SQLite
Fake News Detection | Data Mining Project (Individual) Jun 2026 - Aug 2026
Built a text classification model to detect fake news articles using NLP techniques.
Python, scikit-learn, pandas
"""
result = _parse_text(BACK_TO_BACK_PROJECTS.strip())
print("projects:", result["projects"])
failures = 0


def check(label: str, condition: bool) -> None:
    global failures
    print(f"{label:70s} {'ok' if condition else 'FAILED'}")
    if not condition:
        failures += 1


check("back-to-back projects (no blank line) split into 2 entries", len(result["projects"]) == 2)
if len(result["projects"]) == 2:
    check("entry 1 starts with the first project's title line",
          result["projects"][0].startswith("Grad2Kerja"))
    check("entry 2 starts with the second project's title line",
          result["projects"][1].startswith("Fake News Detection"))

if failures:
    sys.exit(f"{failures} check(s) failed.")
print("\nAll checks passed.")
