"""
Grad2Kerja skill dictionary.

Built from the filtered entry-level JobStreet Malaysia dataset (context-pattern
extraction + manual review). Canonical terms live in SKILLS / LANGUAGES.
ALIASES / LANGUAGE_ALIASES map variant wording to a canonical term.

To grow the dictionary: add the canonical term to SKILLS, and any variants
to ALIASES. Do not add very common English words (e.g. "word") as aliases.
"""

from spacy.matcher import PhraseMatcher
from spacy.tokens import Span
from spacy.util import filter_spans

# ---------------------------------------------------------------- skills
SKILLS = [
    # Software / tools
    "microsoft office", "microsoft excel", "microsoft word", "microsoft powerpoint",
    "google workspace", "autocad", "autocount", "sql accounting", "sap", "wordpress",
    "sql", "html", "c#", "php", "python", "java", "javascript", "asp",
    "adobe photoshop", "adobe illustrator", "adobe premiere pro", "adobe after effects",
    "adobe xd", "canva", "crm systems", "content management systems",
    "data visualization tools", "payroll software", "accounting software",
    "plc programming", "google ads", "mac operating systems", "active directory",
    "erp systems", "computer hardware", "social media analytics tools",

    # Business / domain skills
    "sales", "customer service", "accounting", "accounting principles",
    "accounting standards", "audit", "bookkeeping", "digital marketing", "marketing",
    "social media management", "influencer marketing", "seo", "copywriting",
    "data analysis", "data manipulation", "data modeling", "purchasing", "procurement",
    "sourcing", "human resources", "recruitment", "banking", "call centre",
    "business development", "business strategy", "strategic planning", "finance",
    "financial reporting", "telemarketing", "video editing", "video shooting",
    "mortgage", "spreadsheets", "administration",
    "sales administration", "treasury", "costing", "claims processing",
    "asset management", "accounts payable", "international trade regulations",
    "employment law knowledge", "production planning", "due diligence",
    "credit card processing", "payroll processing", "project management",
    "project documentation", "process optimization", "product development",
    "industrial relations practices",

    # Technical / engineering
    "software development", "application development", "scripting", "networking",
    "troubleshooting", "restful apis", "mvc architecture", "continuous integration",
    "secure coding practices", "electronics", "wiring",
    "reading schematics", "3d design", "graphic design", "design fundamentals",
    "manufacturing line", "lab equipment", "laboratory procedures",

    # Added from weak-category mining (Education, Construction, Healthcare, F&B)
    "interpersonal skills", "product knowledge", "lesson planning",
    "classroom management", "early childhood education", "teaching methods",
    "quantity surveying", "final accounts", "progress claims", "site valuation",
    "patient care", "medication review", "food preparation", "outlet operations",
    "cost control", "infection control", "legal documentation", "teaching materials",
    "continuous improvement", "record keeping",

    # General / soft
    "basic computer skills", "communication skills", "teamwork", "time management",
    "problem solving", "data entry",
]

ALIASES = {
    # Microsoft
    "ms office": "microsoft office",
    "microsoft office applications": "microsoft office",
    "microsoft office suite": "microsoft office",
    "ms office applications": "microsoft office",
    "microsoft office software": "microsoft office",
    "microsoft applications": "microsoft office",
    "office software": "microsoft office",
    "office 365": "microsoft office",
    "excel": "microsoft excel",
    "ms excel": "microsoft excel",
    "ms word": "microsoft word",          # NOT plain "word" (too ambiguous)
    "powerpoint": "microsoft powerpoint",
    "ms powerpoint": "microsoft powerpoint",
    # Adobe
    "photoshop": "adobe photoshop",
    "illustrator": "adobe illustrator",
    "premiere pro": "adobe premiere pro",
    "after effects": "adobe after effects",
    "after effect": "adobe after effects",
    # Programming / IT
    "html5": "html",
    "restful api": "restful apis",
    "computerized accounting systems": "accounting software",
    "sql accounting software": "sql accounting",
    # Business
    "hr": "human resources",
    "auditing": "audit",
    "call center": "call centre",
    "social media": "social media management",
    "social media platforms": "social media management",
    "social media content creation": "social media management",
    "seo best practices": "seo",
    "strategy planning": "strategic planning",
    "account payable": "accounts payable",
    "spreadsheet": "spreadsheets",
    "credit cards": "credit card processing",
    "handling payroll": "payroll processing",
    "payroll processes": "payroll processing",
    "basic accounting principles": "accounting principles",
    "relevant accounting standards": "accounting standards",
    "labor laws": "employment law knowledge",
    "employment laws": "employment law knowledge",
    "employment act": "employment law knowledge",
    "malaysian labor laws": "employment law knowledge",
    # Weak-category additions
    "good interpersonal skills": "interpersonal skills",
    "lesson plans": "lesson planning",
    "lesson plan": "lesson planning",
    "creative teaching methods": "teaching methods",
    "final account": "final accounts",
    "outlet operation": "outlet operations",
    "quantity survey": "quantity surveying",
    "quantity surveyor": "quantity surveying",
    "progress claim": "progress claims",
    "legal documents": "legal documentation",
    "teaching material": "teaching materials",
    "exceptional customer service": "customer service",
    "team player": "teamwork",
    "administrative support": "administration",
    "accurate records": "record keeping",
    "good communication skills": "communication skills",
    "excellent communication": "communication skills",
    "good communication": "communication skills",
    "excellent customer service": "customer service",
    # General
    "computer skills": "basic computer skills",
    "computer operation": "basic computer skills",
    "basic computer operation": "basic computer skills",
}

# ------------------------------------------------------------- languages
# Kept separate from SKILLS, as in the report (Section 3.5).
LANGUAGES = [
    "english", "mandarin", "bahasa malaysia", "cantonese", "japanese",
]

LANGUAGE_ALIASES = {
    "mandarin language": "mandarin",
    "chinese": "mandarin",
    "bahasa melayu": "bahasa malaysia",
    "malay": "bahasa malaysia",
}


# --------------------------------------------------------------- helpers
def _check(terms, aliases):
    missing = [c for c in aliases.values() if c not in terms]
    assert not missing, f"Alias targets not in term list: {missing}"
    dupes = {t for t in terms if terms.count(t) > 1}
    assert not dupes, f"Duplicate terms: {dupes}"


_check(SKILLS, ALIASES)
_check(LANGUAGES, LANGUAGE_ALIASES)


def build_matcher(nlp, terms, aliases):
    """PhraseMatcher where each canonical term is its own label."""
    patterns = {t: [nlp.make_doc(t)] for t in terms}
    for alias, canonical in aliases.items():
        patterns[canonical].append(nlp.make_doc(alias))
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    for canonical, pats in patterns.items():
        matcher.add(canonical, pats)
    return matcher


def extract_terms(text, nlp, matcher):
    """Return the set of canonical terms found in text (longest match wins)."""
    doc = nlp(text)
    spans = [
        Span(doc, start, end, label=nlp.vocab.strings[match_id])
        for match_id, start, end in matcher(doc)
    ]
    return {span.label_ for span in filter_spans(spans)}