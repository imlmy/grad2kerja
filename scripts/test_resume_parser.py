"""Run modules.resume_parser against a real resume PDF and print the result.

Usage:
    venv/Scripts/python scripts/test_resume_parser.py [path/to/resume.pdf]

Defaults to data/sample_resume.pdf if no path is given.
"""
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from modules.resume_parser import parse_resume

pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/sample_resume.pdf")
if not pdf_path.exists():
    sys.exit(f"No such file: {pdf_path}")

t0 = time.time()
try:
    result = parse_resume(pdf_path)
except ValueError as e:
    sys.exit(f"Could not parse {pdf_path.name}: {e}")
elapsed = time.time() - t0

print(f"Parsed {pdf_path.name} in {elapsed:.2f}s\n")
print(f"Text ({len(result['text'])} chars):")
print(result["text"][:300], "..." if len(result["text"]) > 300 else "")

print(f"\nSkills ({len(result['skills'])}):")
for s in result["skills"]:
    print(" -", s)

print(f"\nLanguages ({len(result['languages'])}):")
for l in result["languages"]:
    print(" -", l)

print(f"\nUnrecognised terms ({len(result['unrecognised_terms'])}):")
for t in result["unrecognised_terms"]:
    print(" -", t)

for section in ("education", "experience", "projects"):
    blocks = result[section]
    print(f"\n{section.capitalize()} ({len(blocks)} block(s)):")
    for b in blocks:
        print(" -", b[:150].replace("\n", " "))
