"""Request bodies for the JSON endpoints. Multipart endpoints take Form/File fields directly."""
import re

from pydantic import BaseModel, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _strip_name(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("Name cannot be empty.")
    return v


def _require_digit(v: str) -> str:
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must be at least 8 characters, including one number.")
    return v


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        return _strip_name(v)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address.")
        return v

    @field_validator("password")
    @classmethod
    def _valid_password(cls, v: str) -> str:
        return _require_digit(v)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, v: str) -> str:
        return v.strip().lower()


class ProfileUpdate(BaseModel):
    """PATCH /profile: only the fields given are changed. Email is not editable here -- it's
    shown read-only in the UI, with no change-email flow (see UC002)."""
    name: str | None = Field(None, min_length=1, max_length=100)
    field_of_study: str | None = Field(None, max_length=100)
    location: str | None = Field(None, max_length=200)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, v: str | None) -> str | None:
        return None if v is None else _strip_name(v)

    @field_validator("field_of_study", "location")
    @classmethod
    def _clean_optional_text(cls, v: str | None) -> str | None:
        return None if v is None else v.strip()


class RecommendRequest(BaseModel):
    resume_id: int
    k: int = Field(20, ge=1, le=100)
    category: str | None = None
    location: str | None = None
    type: str | None = None


class SkillGapRequest(BaseModel):
    """UC008 step 8: the AI explanation is generated automatically (explain defaults to True).
    Callers that don't display it (e.g. the dashboard's summary card) should pass explain=False
    to skip the LLM call rather than pay for an explanation nothing shows."""
    resume_id: int
    job_id: int
    explain: bool = True


class SavedJobRequest(BaseModel):
    job_id: int


class ResumeUpdate(BaseModel):
    """PATCH /resumes/{id}: only the fields given are changed."""
    skills: list[str] | None = None
    languages: list[str] | None = None
    education: list[str] | None = None
    experience: list[str] | None = None
    projects: list[str] | None = None


class InterviewCreate(BaseModel):
    job_id: int
    n: int = Field(5, ge=1, le=10)


class AnswerSubmit(BaseModel):
    """POST /interviews/{id}/answers. Audio isn't accepted here -- it's transcribed separately
    via POST /interviews/transcribe first, so the transcript can be reviewed before this call."""
    question_id: int
    text: str
    transcribed: bool = False
