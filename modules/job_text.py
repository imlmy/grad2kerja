"""Shared job-embedding text logic: skill/language extraction and the embedding text format.

Imported by notebooks/encode_mpnet_lean.py and notebooks/02_embeddings.ipynb so the two can't
define this differently and silently drift apart -- a mismatch here once produced a cached
encoding built from a stale skill_dictionary.py that the notebook couldn't detect.
"""
import hashlib

import pandas as pd
import spacy

from modules.skill_dictionary import (
    SKILLS, ALIASES, LANGUAGES, LANGUAGE_ALIASES, build_matcher, extract_terms,
)


def extract_skills_and_languages(jobs: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of jobs with 'skills' and 'languages' columns added (";"-joined, sorted),
    matched against the current modules/skill_dictionary.py."""
    nlp = spacy.load("en_core_web_sm", disable=["tagger", "parser", "ner", "lemmatizer", "attribute_ruler"])
    skill_matcher = build_matcher(nlp, SKILLS, ALIASES)
    language_matcher = build_matcher(nlp, LANGUAGES, LANGUAGE_ALIASES)

    descriptions = jobs["descriptions"].fillna("").tolist()
    jobs = jobs.copy()
    jobs["skills"] = ["; ".join(sorted(extract_terms(d, nlp, skill_matcher))) for d in descriptions]
    jobs["languages"] = ["; ".join(sorted(extract_terms(d, nlp, language_matcher))) for d in descriptions]
    return jobs


def embedding_text(row) -> str:
    """Format: "{job_title}. {subcategory}. Skills: {skills}. {description}" -- title and skills
    come first because the embedding model truncates long inputs."""
    title = row["job_title"] if pd.notna(row["job_title"]) else ""
    subcategory = row["subcategory"] if pd.notna(row["subcategory"]) else ""
    description = row["descriptions"] if pd.notna(row["descriptions"]) else ""
    return f"{title}. {subcategory}. Skills: {row['skills']}. {description}"


def build_texts(jobs: pd.DataFrame) -> list[str]:
    return jobs.apply(embedding_text, axis=1).tolist()


def hash_texts(texts: list[str]) -> str:
    """Deterministic hash of the embedding texts, to detect a stale/mismatched cached encoding."""
    h = hashlib.sha256()
    for t in texts:
        h.update(t.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()
