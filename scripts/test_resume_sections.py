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
