"""Job recommendation: rank precomputed job embeddings against a parsed resume."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from modules.config import MODEL_NAME

ROOT = Path(__file__).resolve().parent.parent

_jobs = pd.read_csv(ROOT / "data" / "jobs_entry_skills.csv")
for _col in ("skills", "category", "location", "type"):
    _jobs[_col] = _jobs[_col].fillna("")
_embeddings = np.load(ROOT / "data" / "job_embeddings.npy")
if len(_jobs) != len(_embeddings):
    raise RuntimeError("job_embeddings.npy and jobs_entry_skills.csv have different row counts")
_job_skill_sets = [set(s.split("; ")) if s else set() for s in _jobs["skills"]]


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def preload_model() -> None:
    """Load the embedding model now instead of on the first request, so the first call to
    recommend_jobs() doesn't pay the (several-second) load cost on top of the ranking itself."""
    _model()


def _embed_resume(resume: dict) -> np.ndarray:
    """Embed a resume the same way jobs were embedded: skills first, then the text."""
    text = f"Skills: {'; '.join(resume['skills'])}. {resume['text']}"
    return _model().encode(text, normalize_embeddings=True)


def _filter_mask(filters: dict) -> np.ndarray:
    mask = np.ones(len(_jobs), dtype=bool)
    for key, value in filters.items():
        if value is None:
            continue
        value = value.lower()
        if key == "category":
            mask &= _jobs["category"].str.lower().eq(value).to_numpy()
        elif key == "location":
            mask &= _jobs["location"].str.lower().str.contains(value, regex=False).to_numpy()
        elif key == "type":
            mask &= _jobs["type"].str.lower().eq(value).to_numpy()
        else:
            raise ValueError(f"Unknown filter '{key}'. Use category, location or type.")
    return mask


def match_job(resume: dict, job_id: int) -> dict | None:
    """Semantic match_pct and matched_skills for one specific job against a resume -- same
    embedding and cosine similarity as recommend_jobs(), just for a single job instead of
    ranking all of them. Returns None if job_id isn't in the dataset."""
    rows = np.flatnonzero(_jobs["job_id"].to_numpy() == job_id)
    if len(rows) == 0:
        return None
    row = rows[0]
    score = float(_embeddings[row] @ _embed_resume(resume))
    match_pct = max(0, min(100, round(score * 100)))
    resume_skills = set(resume["skills"])
    return {"match_pct": match_pct, "matched_skills": sorted(resume_skills & _job_skill_sets[row])}


def recommend_jobs(resume: dict, k: int = 20, filters: dict | None = None) -> pd.DataFrame:
    """Return the top-k jobs for a resume (output of parse_resume), best first.

    filters: optional dict with any of 'category' (exact), 'location' (substring) and 'type'
    (exact), case-insensitive. Filtering happens before ranking, so top-k is within the filtered set.
    """
    candidates = np.flatnonzero(_filter_mask(filters or {}))
    query = _embed_resume(resume)

    scores = _embeddings[candidates] @ query
    top = np.argsort(-scores)[:k]
    rows = candidates[top]

    resume_skills = set(resume["skills"])
    return pd.DataFrame({
        "job_id": _jobs["job_id"].to_numpy()[rows],
        "title": _jobs["job_title"].to_numpy()[rows],
        "company": _jobs["company"].to_numpy()[rows],
        "location": _jobs["location"].to_numpy()[rows],
        "category": _jobs["category"].to_numpy()[rows],
        "score": scores[top].round(4),
        "match_pct": np.round(scores[top] * 100).astype(int),
        "matched_skills": [sorted(resume_skills & _job_skill_sets[r]) for r in rows],
    })
