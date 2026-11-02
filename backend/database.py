"""SQLite storage. Path comes from GRAD2KERJA_DB (default data/app.db)."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("GRAD2KERJA_DB", ROOT / "data" / "app.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    filename TEXT NOT NULL,
    text TEXT NOT NULL,
    skills TEXT NOT NULL,
    languages TEXT NOT NULL,
    education TEXT NOT NULL DEFAULT '[]',
    experience TEXT NOT NULL DEFAULT '[]',
    projects TEXT NOT NULL DEFAULT '[]',
    unrecognised_terms TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS recommendations (
    user_id INTEGER NOT NULL REFERENCES users(id),
    job_id INTEGER NOT NULL,
    match_pct INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, job_id)
);
CREATE TABLE IF NOT EXISTS skill_matches (
    user_id INTEGER NOT NULL REFERENCES users(id),
    job_id INTEGER NOT NULL,
    match_pct REAL,
    matched TEXT NOT NULL,
    missing TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, job_id)
);
CREATE TABLE IF NOT EXISTS saved_jobs (
    user_id INTEGER NOT NULL REFERENCES users(id),
    job_id INTEGER NOT NULL,
    saved_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, job_id)
);
CREATE TABLE IF NOT EXISTS interview_sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    job_id INTEGER NOT NULL,
    personalised INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS interview_questions (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES interview_sessions(id),
    position INTEGER NOT NULL,
    question TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'general'
);
CREATE TABLE IF NOT EXISTS interview_answers (
    id INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES interview_questions(id),
    answer TEXT NOT NULL,
    transcribed INTEGER NOT NULL,
    score INTEGER NOT NULL,
    strengths TEXT NOT NULL,
    improvements TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript(SCHEMA)
        _migrate_users_table(conn)
        _migrate_resumes_table(conn)
        _migrate_interview_questions_table(conn)
        _migrate_interview_sessions_table(conn)


def _migrate_users_table(conn: sqlite3.Connection) -> None:
    """Add the columns authentication needs. A plain ALTER TABLE ADD COLUMN can't declare a
    column UNIQUE in SQLite, so uniqueness is enforced with a separate index instead (NULL emails
    from before this feature don't conflict with each other under a unique index)."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    for column in ("email", "password_hash"):
        if column not in existing:
            conn.execute(f"ALTER TABLE users ADD COLUMN {column} TEXT")
    for column in ("field_of_study", "location"):
        if column not in existing:
            conn.execute(f"ALTER TABLE users ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")


def _migrate_resumes_table(conn: sqlite3.Connection) -> None:
    """Add columns introduced after the first deployed schema, so an existing data/app.db
    doesn't need to be deleted when the schema grows."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(resumes)")}
    for column in ("education", "experience", "projects"):
        if column not in existing:
            conn.execute(f"ALTER TABLE resumes ADD COLUMN {column} TEXT NOT NULL DEFAULT '[]'")
    if "size_bytes" not in existing:
        conn.execute("ALTER TABLE resumes ADD COLUMN size_bytes INTEGER NOT NULL DEFAULT 0")


def _migrate_interview_questions_table(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(interview_questions)")}
    if "type" not in existing:
        conn.execute("ALTER TABLE interview_questions ADD COLUMN type TEXT NOT NULL DEFAULT 'general'")


def _migrate_interview_sessions_table(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(interview_sessions)")}
    if "personalised" not in existing:
        conn.execute("ALTER TABLE interview_sessions ADD COLUMN personalised INTEGER NOT NULL DEFAULT 0")
