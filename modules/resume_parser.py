"""
Resume parsing: extract text, skills, languages, section text and unrecognised terms from a
resume PDF. Skills/languages are matched against modules/skill_dictionary.py; noun chunks the
dictionary misses are fuzzy-matched against the same dictionary, and anything still unmatched is
returned as unrecognised_terms instead of getting dropped.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import pdfplumber
import spacy
from rapidfuzz import fuzz, process

from modules.skill_dictionary import (
    SKILLS, ALIASES, LANGUAGES, LANGUAGE_ALIASES, build_matcher, extract_terms,
)

_FUZZY_CUTOFF = 88
_STRIP_BULLET = re.compile(r"^[-•*•\s]+")
_STRIP_LEADING = re.compile(
    r"^(the|a|an|our|your|their|this|that|any|"
    r"strong|good|solid|excellent|basic|advanced|proficient|working)\s+"
)
_COLLAPSE_WS = re.compile(r"\s+")

# ner/lemmatizer disabled: unused here, noun_chunks only needs tagger + parser + attribute_ruler
_nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
_skill_matcher = build_matcher(_nlp, SKILLS, ALIASES)
_language_matcher = build_matcher(_nlp, LANGUAGES, LANGUAGE_ALIASES)

_SKILL_VOCAB = {**{s: s for s in SKILLS}, **ALIASES}
_LANGUAGE_VOCAB = {**{l: l for l in LANGUAGES}, **LANGUAGE_ALIASES}

# Headings that start a section we extract, mapped to the category they belong to. Headings that
# are recognised but not extracted (e.g. "Skills") still end the previous section correctly.
_SECTION_HEADINGS: dict[str, str | None] = {
    "education": "education",
    "academic background": "education",
    "educational background": "education",
    "qualifications": "education",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "employment history": "experience",
    "work history": "experience",
    "internship": "experience",
    "internships": "experience",
    "projects": "projects",
    "academic projects": "projects",
    "personal projects": "projects",
    "project experience": "projects",
    "summary": None,
    "objective": None,
    "profile": None,
    "skills": None,
    "technical skills": None,
    "certifications": None,
    "certificates": None,
    "awards": None,
    "achievements": None,
    "activities": None,
    "extracurricular activities": None,
    "references": None,
    "languages": None,
    "contact": None,
    "personal information": None,
    "personal details": None,
    "interests": None,
    "hobbies": None,
    "publications": None,
    "volunteer experience": None,
    "volunteering": None,
}
_HEADING_PATTERN = re.compile(
    r"^\s*(" + "|".join(re.escape(h) for h in sorted(_SECTION_HEADINGS, key=len, reverse=True)) + r")\s*:?\s*$",
    re.IGNORECASE,
)


def _extract_text(pdf_bytes_or_path: str | Path | bytes) -> str:
    """Extract text from every page of a PDF, given a path or raw bytes.

    Any failure to open or read the file (corrupt PDF, or not a PDF at all despite the
    extension/content-type check at the API boundary) is raised as ValueError, same as the
    "no text layer" case below -- one error type for every "this PDF is unusable" reason, so
    callers (e.g. backend/main.py's ValueError -> 422 handler) don't need to know pdfplumber's
    internal exception types."""
    source = io.BytesIO(pdf_bytes_or_path) if isinstance(pdf_bytes_or_path, bytes) else pdf_bytes_or_path
    try:
        with pdfplumber.open(source) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except ValueError:
        raise
    except Exception as e:
        raise ValueError("This PDF could not be read.") from e
    return "\n".join(pages).strip()


def _extract_sections(text: str) -> dict[str, list[str]]:
    """Split text by common section headings (a recognised heading alone on its own line).

    Returns {"education": [...], "experience": [...], "projects": [...]}, each a list of text
    blocks -- a category can have more than one heading (e.g. "Experience" and "Internships").
    A heading not in one of these three categories (e.g. "Skills") still ends the section before
    it, but its own content isn't collected. A missing category returns an empty list.
    """
    sections: dict[str, list[str]] = {"education": [], "experience": [], "projects": []}
    current: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if current and buffer:
            block = "\n".join(buffer).strip()
            if block:
                sections[current].append(block)

    for line in text.splitlines():
        m = _HEADING_PATTERN.match(line)
        if m:
            flush()
            current = _SECTION_HEADINGS[m.group(1).lower()]
            buffer = []
        else:
            buffer.append(line)
    flush()
    return sections


def _fuzzy_match(term: str) -> tuple[str, str] | None:
    """Fuzzy-match a noun chunk against the skill/language vocabularies.

    Returns (canonical_term, "skill" | "language"), or None if nothing scores above the cutoff.
    """
    for vocab, kind in ((_SKILL_VOCAB, "skill"), (_LANGUAGE_VOCAB, "language")):
        # fuzz.ratio, not WRatio -- WRatio's partial-ratio scored "malaysia" a 90 against
        # "malaysian labor laws", a false positive plain ratio doesn't have.
        match = process.extractOne(term, vocab.keys(), scorer=fuzz.ratio, score_cutoff=_FUZZY_CUTOFF)
        if match:
            return vocab[match[0]], kind
    return None


def _noun_chunks(doc) -> set[str]:
    """Normalised, deduplicated noun chunks: lowercase, bullets/determiners stripped, whitespace
    collapsed, short ones dropped."""
    chunks = set()
    for chunk in doc.noun_chunks:
        text = _COLLAPSE_WS.sub(" ", chunk.text.strip().lower())
        text = _STRIP_LEADING.sub("", _STRIP_BULLET.sub("", text))
        if len(text) > 2:
            chunks.add(text)
    return chunks


def _parse_text(text: str) -> dict:
    """The text-analysis half of parse_resume(), split out so it can be tested directly against
    sample strings without needing a real PDF. See parse_resume() for the full contract."""
    skills = set(extract_terms(text, _nlp, _skill_matcher))
    languages = set(extract_terms(text, _nlp, _language_matcher))

    # Period inserted at line breaks so spaCy treats bullet lines as sentence boundaries;
    # only affects chunk parsing below, not the returned text or the matching above.
    chunk_doc = _nlp(text.replace("\n", ". \n"))

    unrecognised_terms = set()
    for chunk in _noun_chunks(chunk_doc):
        if chunk in skills or chunk in languages:
            continue
        match = _fuzzy_match(chunk)
        if match:
            canonical, kind = match
            (skills if kind == "skill" else languages).add(canonical)
        else:
            unrecognised_terms.add(chunk)

    sections = _extract_sections(text)

    return {
        "text": text,
        "skills": sorted(skills),
        "languages": sorted(languages),
        "education": sections["education"],
        "experience": sections["experience"],
        "projects": sections["projects"],
        # Internal only: for future manual dictionary review. Never show these in the UI or add
        # them to modules/skill_dictionary.py automatically -- the dictionary is human-reviewed.
        "unrecognised_terms": sorted(unrecognised_terms),
    }


def parse_resume(pdf_bytes_or_path: str | Path | bytes) -> dict:
    """Parse a resume PDF into text, skills, languages, section text and unrecognised terms.

    No skills or languages found is not an error -- it returns empty lists, since the user can
    edit the result afterwards. Raises ValueError only if no text could be extracted at all (e.g.
    a scanned/image-only PDF with no text layer; OCR is not supported).
    """
    text = _extract_text(pdf_bytes_or_path)
    if not text:
        raise ValueError(
            "No text could be extracted from this PDF. It may be a scanned image without "
            "a text layer, which this parser cannot read."
        )
    return _parse_text(text)
