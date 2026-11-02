"""Run modules.matching against the sample resume and print the top jobs with timings.

Usage:
    venv/Scripts/python scripts/test_matching.py
"""
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from modules.matching import match_job, recommend_jobs
from modules.resume_parser import parse_resume

pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 60)

resume = parse_resume(Path("data/sample_resume.pdf"))

t0 = time.time()
df = recommend_jobs(resume, k=5)
cold = time.time() - t0

t0 = time.time()
recommend_jobs(resume, k=20)
warm = time.time() - t0

print(f"Top 5 (no filters) -- first call {cold:.2f}s (includes model load), repeat call {warm:.2f}s\n")
print(df.to_string(index=False))

t0 = time.time()
filtered = recommend_jobs(resume, k=5, filters={"category": "Accounting", "type": "Full time"})
print(f"\nTop 5 in Accounting, Full time -- {time.time() - t0:.2f}s\n")
print(filtered.to_string(index=False))

print("\n=== match_job ===")
top_job_id = int(df.iloc[0]["job_id"])
single = match_job(resume, top_job_id)
print(f"match_job for the top-ranked job ({top_job_id}): {single}")
assert single["match_pct"] == int(df.iloc[0]["match_pct"]), \
    "match_job should score a job identically to recommend_jobs"

no_skills_job_id = 74677668  # a real job_id with no skills listed, per the dataset
no_skills_result = match_job(resume, no_skills_job_id)
print(f"match_job for a job with no listed skills ({no_skills_job_id}): {no_skills_result}")
assert no_skills_result is not None and no_skills_result["matched_skills"] == [], \
    "a job with no skills should still return a match_pct, with an empty matched_skills list"

assert match_job(resume, 999999999) is None, "an unknown job_id should return None, not raise"
print("match_job checks passed.")
