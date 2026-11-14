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


# ------------------------------------------------- round 6 (Nov 2026)
# Mined from the entry-level dataset: ICT technical terms plus the largest other
# categories (Accounting, Admin, Engineering, Sales, Manufacturing, HR, Marketing,
# Banking, Call Centre). Candidates needed >= 5 postings from >= 3 companies and were
# reviewed manually (keep / alias / drop). Ambiguous words were excluded or made
# case-sensitive (see CASE_SENSITIVE).
SKILLS += [
    ".net", "accounts receivable", "adobe indesign", "agile methodology", "ajax", "angular",
    "anti-money laundering", "api integration", "applicant tracking systems",
    "autodesk revit", "aws", "bank reconciliation", "bill of materials",
    "bill of quantities", "bim", "bootstrap", "budgeting and forecasting",
    "business correspondence", "c++", "cad software", "calendar management",
    "cisco networking", "cnc machining", "commissioning", "company secretarial",
    "compensation and benefits", "complaint handling", "content creation", "credit control",
    "css", "cybersecurity", "data structures", "design for testability",
    "design of experiments", "design patterns", "design verification", "devops",
    "distributed control systems", "django", "docker", "document management", "e-commerce",
    "eda tools", "electronic test equipment", "email marketing", "employee engagement",
    "employee relations", "etl", "event management", "express.js", "figma", "filing",
    "financial analysis", "firebase", "fixed asset accounting", "flask", "flutter", "fmea",
    "fpga", "general ledger", "golang", "good manufacturing practice", "google analytics",
    "google cloud platform", "haccp", "halal compliance", "hmi", "hrd corp claims", "hris",
    "hvac", "import and export documentation", "instrumentation", "inventory management",
    "invoicing", "it support", "itil", "jira", "journal entries", "jquery", "json", "jsp",
    "kotlin", "kubernetes", "kyc", "labview", "laravel", "lead generation", "linux",
    "live chat support", "machine learning", "material requirements planning",
    "microservices", "microsoft azure", "microsoft outlook", "microsoft power automate",
    "microsoft project", "microsoft sharepoint", "microsoft sql server", "microsoft visio",
    "minute taking", "mobile app development", "mongodb", "myob", "mysql", "negotiation",
    "network security", "new product introduction", "next.js", "node.js", "nosql",
    "object-oriented programming", "occupational safety and health",
    "office equipment operation", "office supplies management", "onboarding", "orm",
    "payment processing", "pcb assembly", "performance management", "postgresql",
    "power bi", "public relations", "quality assurance", "quality control",
    "quality management systems", "quickbooks", "quotation preparation", "react",
    "react native", "redis", "relational databases", "robotic process automation",
    "rtl design", "sales and service tax", "scada", "search engine marketing", "selenium",
    "servicenow", "software development life cycle", "software testing", "solidworks",
    "spring boot", "statistical process control", "supply chain management", "swift",
    "tableau", "taxation", "telephone handling", "travel arrangements", "typescript",
    "typing", "ubs accounting", "ui/ux design", "uml", "unit testing", "unix",
    "user acceptance testing", "vb.net", "vba", "version control (git)", "virtualization",
    "vue.js", "warehouse management", "web servers", "web services", "windows server",
    "xero", "xml",
]

ALIASES.update({
    "payroll system": "payroll software",
    "payroll administration": "payroll processing",
    "payroll reporting": "payroll processing",
    "payroll records": "payroll processing",
    "ci/cd": "continuous integration",
    ".net core": ".net",
    "a/p": "accounts payable",
    "a/r": "accounts receivable",
    "account receivable": "accounts receivable",
    "accounting entries": "journal entries",
    "accounting system": "accounting software",
    "accruals": "journal entries",
    "acmv": "hvac",
    "agile development": "agile methodology",
    "agile methodologies": "agile methodology",
    "ahu": "hvac",
    "amazon web services": "aws",
    "aml": "anti-money laundering",
    "aml/cft": "anti-money laundering",
    "angular.js": "angular",
    "angularjs": "angular",
    "answering phone calls": "telephone handling",
    "answering phones": "telephone handling",
    "apache": "web servers",
    "asp.net": ".net",
    "auditing principles": "audit",
    "auditing standards": "audit",
    "auto cad": "autocad",
    "autocount accounting software": "autocount",
    "azure": "microsoft azure",
    "balance sheet": "financial reporting",
    "balance sheets": "financial reporting",
    "bank reconciliations": "bank reconciliation",
    "bash": "scripting",
    "benefits administration": "compensation and benefits",
    "bill of lading": "import and export documentation",
    "bitbucket": "version control (git)",
    "blog posts": "copywriting",
    "bom": "bill of materials",
    "booking flights": "travel arrangements",
    "bookkeeping procedures": "bookkeeping",
    "boq": "bill of quantities",
    "bq": "bill of quantities",
    "budgeting": "budgeting and forecasting",
    "cabling": "networking",
    "cad": "cad software",
    "cad/cam": "cad software",
    "candidate sourcing": "recruitment",
    "capcut": "video editing",
    "cash book": "bookkeeping",
    "cash flow statements": "financial reporting",
    "cash management": "treasury",
    "ccna": "cisco networking",
    "ccnp": "cisco networking",
    "cisco": "cisco networking",
    "cms": "content management systems",
    "cnc": "cnc machining",
    "code versioning tools": "version control (git)",
    "cold calling": "telemarketing",
    "complaint management processes": "complaint handling",
    "computerized accounting": "accounting software",
    "conducting reference checks": "recruitment",
    "copying": "office equipment operation",
    "cost accounting": "costing",
    "crm software": "crm systems",
    "css3": "css",
    "cyber security": "cybersecurity",
    "data structures and algorithms": "data structures",
    "dbms": "relational databases",
    "dcs": "distributed control systems",
    "delivery order": "import and export documentation",
    "design software": "cad software",
    "desktop support": "it support",
    "dft": "design for testability",
    "dhcp": "networking",
    "digital marketing tools": "digital marketing",
    "dns": "networking",
    "document filing": "filing",
    "document preparation": "document management",
    "dosh": "occupational safety and health",
    "dotnet": ".net",
    "e-commerce platforms": "e-commerce",
    "edm": "email marketing",
    "edr": "cybersecurity",
    "ehs": "occupational safety and health",
    "express js": "express.js",
    "expressjs": "express.js",
    "facebook": "social media management",
    "fax machines": "office equipment operation",
    "faxing": "office equipment operation",
    "fifo": "inventory management",
    "financial reports": "financial reporting",
    "financial software": "accounting software",
    "firewall": "network security",
    "firewalls": "network security",
    "fixed assets": "fixed asset accounting",
    "forecasting": "budgeting and forecasting",
    "frs": "accounting standards",
    "fssc": "haccp",
    "full set accounts": "final accounts",
    "gaap": "accounting standards",
    "gcp": "google cloud platform",
    "general ledger entries": "general ledger",
    "git": "version control (git)",
    "github": "version control (git)",
    "gitlab": "version control (git)",
    "gmp": "good manufacturing practice",
    "google cloud": "google cloud platform",
    "google drive": "google workspace",
    "google suite": "google workspace",
    "graphic design software": "graphic design",
    "halal": "halal compliance",
    "hana": "sap",
    "handling correspondence": "business correspondence",
    "hibernate": "orm",
    "hr administration": "human resources",
    "hrd": "hrd corp claims",
    "hrd corp": "hrd corp claims",
    "hrdc": "hrd corp claims",
    "hrdf": "hrd corp claims",
    "hris software": "hris",
    "hrms": "hris",
    "hse": "occupational safety and health",
    "hyper-v": "virtualization",
    "ifrs": "accounting standards",
    "iis": "web servers",
    "import/export": "import and export documentation",
    "income statements": "financial reporting",
    "income tax": "taxation",
    "income tax act": "taxation",
    "indesign": "adobe indesign",
    "instagram": "social media management",
    "integration testing": "software testing",
    "internal audit": "audit",
    "inventory": "inventory management",
    "invoice processing": "invoicing",
    "iso 9001": "quality management systems",
    "it technical support": "it support",
    "itsm": "itil",
    "java server pages": "jsp",
    "jenkins": "continuous integration",
    "job boards": "recruitment",
    "job posting": "recruitment",
    "job postings": "recruitment",
    "journals": "journal entries",
    "js": "javascript",
    "k8s": "kubernetes",
    "kanban": "agile methodology",
    "know your customer": "kyc",
    "kol": "influencer marketing",
    "labour law": "employment law knowledge",
    "lan": "networking",
    "laravel framework": "laravel",
    "lazada": "e-commerce",
    "live chat": "live chat support",
    "live chats": "live chat support",
    "logic analyzers": "electronic test equipment",
    "macos": "mac operating systems",
    "maintaining office supplies": "office supplies management",
    "maintaining records": "record keeping",
    "managing calendars": "calendar management",
    "managing correspondence": "business correspondence",
    "mariadb": "mysql",
    "meeting minutes": "minute taking",
    "memos": "business correspondence",
    "mfrs": "accounting standards",
    "mobile application development": "mobile app development",
    "mpers": "accounting standards",
    "mrp": "material requirements planning",
    "ms outlook": "microsoft outlook",
    "ms project": "microsoft project",
    "ms sql": "microsoft sql server",
    "mssql": "microsoft sql server",
    "multimeter": "electronic test equipment",
    "mvc": "mvc architecture",
    "negotiate": "negotiation",
    "negotiate/close": "negotiation",
    "negotiation skills": "negotiation",
    "newsletters": "email marketing",
    "nextjs": "next.js",
    "nginx": "web servers",
    "niosh": "occupational safety and health",
    "node js": "node.js",
    "nodejs": "node.js",
    "npi": "new product introduction",
    "object oriented programming": "object-oriented programming",
    "object-relational mapping": "orm",
    "offboarding": "onboarding",
    "office equipment": "office equipment operation",
    "ohsas": "occupational safety and health",
    "online advertising": "search engine marketing",
    "oop": "object-oriented programming",
    "ordering supplies": "office supplies management",
    "oscilloscopes": "electronic test equipment",
    "osh": "occupational safety and health",
    "osha": "occupational safety and health",
    "osi model": "networking",
    "outbound calls": "telemarketing",
    "outlook": "microsoft outlook",
    "packing list": "import and export documentation",
    "payables": "accounts payable",
    "payment collection": "credit control",
    "payroll": "payroll processing",
    "pcba": "pcb assembly",
    "performance reviews": "performance management",
    "peripherals": "computer hardware",
    "perl": "scripting",
    "petty cash": "bookkeeping",
    "pfmea": "fmea",
    "photocopying": "office equipment operation",
    "plc": "plc programming",
    "postgres": "postgresql",
    "posting job openings": "recruitment",
    "power automate": "microsoft power automate",
    "powerbi": "power bi",
    "powershell": "scripting",
    "ppc": "search engine marketing",
    "preparing documents": "document management",
    "press releases": "public relations",
    "processing invoices": "invoicing",
    "prospecting": "lead generation",
    "pytorch": "machine learning",
    "qms": "quality management systems",
    "quotations": "quotation preparation",
    "rdbms": "relational databases",
    "react js": "react",
    "react.js": "react",
    "reactjs": "react",
    "reactnative": "react native",
    "receivables": "accounts receivable",
    "reconciliation": "bank reconciliation",
    "reconciliations": "bank reconciliation",
    "responding to emails": "business correspondence",
    "rest api": "restful apis",
    "rest apis": "restful apis",
    "resume screening": "recruitment",
    "revit": "autodesk revit",
    "router": "networking",
    "routers": "networking",
    "rpa": "robotic process automation",
    "rtl": "rtl design",
    "scheduling appointments": "calendar management",
    "scheduling interviews": "recruitment",
    "scheduling meetings": "calendar management",
    "scm": "supply chain management",
    "screening resumes": "recruitment",
    "scripting languages": "scripting",
    "scrum": "agile methodology",
    "sdlc": "software development life cycle",
    "secretarial compliance": "company secretarial",
    "sharepoint": "microsoft sharepoint",
    "shipping documents": "import and export documentation",
    "shopee": "e-commerce",
    "siem": "cybersecurity",
    "smt": "pcb assembly",
    "soap": "web services",
    "social media marketing": "social media management",
    "social media posts": "social media management",
    "sourcing candidates": "recruitment",
    "spc": "statistical process control",
    "spring framework": "spring boot",
    "springboot": "spring boot",
    "sql accounting system": "sql accounting",
    "sql server": "microsoft sql server",
    "ssis": "etl",
    "sst": "sales and service tax",
    "stationery": "office supplies management",
    "stock control": "inventory management",
    "supply chain": "supply chain management",
    "svn": "version control (git)",
    "system verilog": "rtl design",
    "talent acquisition": "recruitment",
    "tax computation": "taxation",
    "tax submission": "taxation",
    "tcl": "scripting",
    "tcp/ip": "networking",
    "tdd": "software testing",
    "tensorflow": "machine learning",
    "test-driven development": "software testing",
    "tfs": "version control (git)",
    "third party api": "api integration",
    "third-party api": "api integration",
    "tik tok": "social media management",
    "tiktok": "social media management",
    "uat": "user acceptance testing",
    "ubs": "ubs accounting",
    "ubuntu": "linux",
    "ui": "ui/ux design",
    "ui ux": "ui/ux design",
    "ui/ux": "ui/ux design",
    "uipath": "robotic process automation",
    "unit test": "unit testing",
    "user experience design": "ui/ux design",
    "using accounting software": "accounting software",
    "uvm": "design verification",
    "ux": "ui/ux design",
    "ux/ui": "ui/ux design",
    "verilog": "rtl design",
    "version control": "version control (git)",
    "version control systems": "version control (git)",
    "video editing software": "video editing",
    "videography": "video shooting",
    "virtualisation": "virtualization",
    "visio": "microsoft visio",
    "vlan": "networking",
    "vmware": "virtualization",
    "vpn": "networking",
    "vue": "vue.js",
    "vuejs": "vue.js",
    "waf": "cybersecurity",
    "wan": "networking",
    "xhs": "social media management",
    "xiaohongshu": "social media management",
    "youtube": "social media management",
})

# Matched only with this exact capitalisation, because the lowercase word has a
# common non-skill meaning ("react quickly", "Sem 1", "swift response", ...).
CASE_SENSITIVE = {
    "AP": "accounts payable",
    "AR": "accounts receivable",
    "ATS": "applicant tracking systems",
    "Bootstrap": "bootstrap",
    "CRM": "crm systems",
    "Flask": "flask",
    "Flutter": "flutter",
    "GL": "general ledger",
    "ML": "machine learning",
    "QA": "quality assurance",
    "QC": "quality control",
    "React": "react",
    "SEM": "search engine marketing",
    "Swift": "swift",
}


# --------------------------------------------------- soft skills / software tools
# Subsets of SKILLS used to separate "soft" skills (interpersonal qualities, usually shown
# through experience rather than listed on a resume) and "software" (a named application,
# platform or tool) from the rest ("technical": programming languages, frameworks, databases,
# cloud platforms, methods and domain knowledge). Reviewed manually against SKILLS above --
# no other purely soft/personal skill was found beyond this set.
SOFT_SKILLS = {
    "communication skills", "interpersonal skills", "problem solving", "teamwork",
    "time management", "negotiation",
}

SOFTWARE_TOOLS = {
    "microsoft office", "microsoft excel", "microsoft word", "microsoft powerpoint",
    "microsoft outlook", "microsoft project", "microsoft sharepoint", "microsoft visio",
    "microsoft power automate", "google workspace", "google ads", "google analytics",
    "autocad", "autodesk revit", "solidworks", "sap", "autocount", "sql accounting",
    "ubs accounting", "myob", "xero", "quickbooks", "accounting software", "payroll software",
    "erp systems", "crm systems", "hris", "applicant tracking systems", "canva", "wordpress",
    "figma", "jira", "power bi", "tableau", "adobe photoshop", "adobe illustrator",
    "adobe premiere pro", "adobe after effects", "adobe xd", "adobe indesign", "labview",
    "servicenow", "content management systems", "data visualization tools",
    "social media analytics tools", "eda tools", "cad software", "active directory",
}


def skill_type(skill: str) -> str:
    """Classify a canonical skill term as "soft" (an interpersonal quality, usually shown
    through experience rather than listed), "software" (a named application, platform or tool)
    or "technical" (everything else)."""
    if skill in SOFT_SKILLS:
        return "soft"
    if skill in SOFTWARE_TOOLS:
        return "software"
    return "technical"


# --------------------------------------------------------------- helpers
def _check(terms, aliases):
    missing = [c for c in aliases.values() if c not in terms]
    assert not missing, f"Alias targets not in term list: {missing}"
    dupes = {t for t in terms if terms.count(t) > 1}
    assert not dupes, f"Duplicate terms: {dupes}"


_check(SKILLS, ALIASES)
_missing_cs = [c for c in CASE_SENSITIVE.values() if c not in SKILLS]
assert not _missing_cs, f"Case-sensitive targets not in SKILLS: {_missing_cs}"
_check(LANGUAGES, LANGUAGE_ALIASES)

_missing_soft = [s for s in SOFT_SKILLS if s not in SKILLS]
assert not _missing_soft, f"SOFT_SKILLS entries not in SKILLS: {_missing_soft}"
_missing_software = [s for s in SOFTWARE_TOOLS if s not in SKILLS]
assert not _missing_software, f"SOFTWARE_TOOLS entries not in SKILLS: {_missing_software}"
_soft_software_overlap = SOFT_SKILLS & SOFTWARE_TOOLS
assert not _soft_software_overlap, f"Terms in both SOFT_SKILLS and SOFTWARE_TOOLS: {_soft_software_overlap}"


class _Matcher:
    """Case-insensitive PhraseMatcher plus an optional exact-case one; called like a
    PhraseMatcher (returns (match_id, start, end) tuples)."""

    def __init__(self, lower, exact=None):
        self.lower, self.exact = lower, exact

    def __call__(self, doc):
        matches = list(self.lower(doc))
        if self.exact is not None:
            matches += list(self.exact(doc))
        return matches


def build_matcher(nlp, terms, aliases, case_sensitive=None):
    """Matcher where each canonical term is its own label.

    case_sensitive: optional {surface form: canonical term} matched with exact
    capitalisation only (use CASE_SENSITIVE for skills)."""
    # A canonical name that is itself an ambiguous word (e.g. "react") is only matched
    # through its exact-case form in case_sensitive, never case-insensitively.
    exact_only = {s.lower() for s, c in (case_sensitive or {}).items() if s.lower() == c}
    patterns = {t: [] if t in exact_only else [nlp.make_doc(t)] for t in terms}
    for alias, canonical in aliases.items():
        patterns[canonical].append(nlp.make_doc(alias))
    lower = PhraseMatcher(nlp.vocab, attr="LOWER")
    for canonical, pats in patterns.items():
        if pats:
            lower.add(canonical, pats)
    exact = None
    if case_sensitive:
        exact = PhraseMatcher(nlp.vocab, attr="ORTH")
        for surface, canonical in case_sensitive.items():
            exact.add(canonical, [nlp.make_doc(surface)])
    return _Matcher(lower, exact)


def extract_terms(text, nlp, matcher):
    """Return the set of canonical terms found in text (longest match wins)."""
    doc = nlp(text)
    spans = [
        Span(doc, start, end, label=nlp.vocab.strings[match_id])
        for match_id, start, end in matcher(doc)
    ]
    return {span.label_ for span in filter_spans(spans)}