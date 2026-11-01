"""Pydantic data contracts between the 8 agents.

Domain models are persisted in the CRM; "LLM output" models are lean,
structured-output-safe schemas the model fills in. `CandidateProfile.fact_corpus()`
is the source of truth for the anti-fabrication guard.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    DISCOVERED = "discovered"
    EXTRACTED = "extracted"
    RANKED = "ranked"
    ICEBOX = "icebox"
    SELECTED = "selected"
    TAILORED = "tailored"
    DOCUMENT_READY = "document_ready"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUBMITTED = "submitted"
    FAILED = "failed"
    NEEDS_MANUAL = "needs_manual"


class ApplyMode(str, Enum):
    API = "api"
    EMAIL = "email"
    BROWSER = "browser"
    UNKNOWN = "unknown"


class WorkModel(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class Seniority(str, Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    LEAD = "lead"
    MANAGER = "manager"
    UNKNOWN = "unknown"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def normalize_text(text: str) -> str:
    """Accent-free, lowercase, single-spaced text for guard comparisons."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text.lower()).strip()


# --- Candidate profile (the only allowed source of facts) -------------------
class ContactInfo(BaseModel):
    name: str
    email: str
    phone: str | None = None
    location: str | None = None
    links: list[str] = Field(default_factory=list)


class Experience(BaseModel):
    company: str
    title: str
    start: str
    end: str | None = None
    location: str | None = None
    bullets: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: str
    degree: str
    field: str | None = None
    start: str | None = None
    end: str | None = None


class SkillItem(BaseModel):
    name: str
    years: float | None = None
    level: str | None = None


class CandidateProfile(BaseModel):
    contact: ContactInfo
    summary: str = ""
    experiences: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[SkillItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)

    def skill_names(self) -> list[str]:
        return [s.name for s in self.skills]

    def fact_corpus(self) -> str:
        parts: list[str] = [self.summary, self.contact.name, self.contact.location or ""]
        for e in self.experiences:
            parts += [e.company, e.title, e.location or "", e.start, e.end or "atual"]
            parts += e.bullets + e.skills
        for ed in self.education:
            parts += [ed.institution, ed.degree, ed.field or "", ed.start or "", ed.end or ""]
        parts += [s.name for s in self.skills] + self.certifications + self.languages
        return normalize_text(" ".join(p for p in parts if p))


# --- Pipeline artifacts -----------------------------------------------------
class JobLead(BaseModel):
    id: str = Field(default_factory=_new_id)
    source: str
    url: str
    title: str | None = None
    company: str | None = None
    discovered_at: datetime = Field(default_factory=_now)
    content_hash: str | None = None
    raw_snippet: str | None = None

    @staticmethod
    def hash_content(text: str) -> str:
        return hashlib.sha256(normalize_text(text).encode()).hexdigest()[:16]


class StructuredJob(BaseModel):
    lead_id: str
    title: str
    company: str
    location: str | None = None
    work_model: WorkModel = WorkModel.UNKNOWN
    seniority: Seniority = Seniority.UNKNOWN
    must_haves: list[str] = Field(default_factory=list)
    nice_to_haves: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    apply_mode: ApplyMode = ApplyMode.UNKNOWN
    apply_target: str | None = None
    raw_text: str = ""
    extracted_at: datetime = Field(default_factory=_now)


class FitAssessment(BaseModel):
    job_id: str
    interview_probability: float
    score: int
    matched_must: list[str] = Field(default_factory=list)
    missing_must: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    rationale: str = ""
    recommended: bool = False
    assessed_at: datetime = Field(default_factory=_now)


class ResumeBullet(BaseModel):
    text: str
    source_ref: str = ""
    grounded: bool = True


class TailoredExperience(BaseModel):
    company: str
    title: str
    dates: str
    bullets: list[ResumeBullet] = Field(default_factory=list)


class TailoredResume(BaseModel):
    job_id: str
    name: str
    contact_line: str = ""
    headline: str = ""
    summary: str = ""
    experiences: list[TailoredExperience] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    education_lines: list[str] = Field(default_factory=list)
    diff_notes: list[str] = Field(default_factory=list)
    flagged_unsupported: list[str] = Field(default_factory=list)
    tailored_at: datetime = Field(default_factory=_now)

    @property
    def has_unsupported(self) -> bool:
        return bool(self.flagged_unsupported)


class ScreeningQA(BaseModel):
    question: str
    answer: str
    grounded: bool = True


class ApplicationDraft(BaseModel):
    job_id: str
    resume_pdf_path: str
    cover_letter: str | None = None
    screening: list[ScreeningQA] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    status: JobStatus = JobStatus.PENDING_APPROVAL
    created_at: datetime = Field(default_factory=_now)


class SubmissionResult(BaseModel):
    job_id: str
    mode: ApplyMode
    success: bool
    confirmation: str | None = None
    error: str | None = None
    submitted_at: datetime = Field(default_factory=_now)


# --- LLM output schemas -----------------------------------------------------
class JobExtraction(BaseModel):
    title: str
    company: str
    location: str | None = None
    work_model: WorkModel = WorkModel.UNKNOWN
    seniority: Seniority = Seniority.UNKNOWN
    must_haves: list[str] = Field(default_factory=list)
    nice_to_haves: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None


class FitResult(BaseModel):
    interview_probability: float
    score: int
    matched_must: list[str] = Field(default_factory=list)
    missing_must: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    rationale: str


class TailorBullet(BaseModel):
    text: str
    source_ref: str


class TailorExperienceOut(BaseModel):
    company: str
    title: str
    dates: str
    bullets: list[TailorBullet] = Field(default_factory=list)


class TailorOutput(BaseModel):
    headline: str = ""
    summary: str = ""
    experiences: list[TailorExperienceOut] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    diff_notes: list[str] = Field(default_factory=list)


class FactCheckOutput(BaseModel):
    unsupported_claims: list[str] = Field(default_factory=list)
    notes: str = ""


class AuditEntry(BaseModel):
    id: str = Field(default_factory=_new_id)
    ts: datetime = Field(default_factory=_now)
    action: str
    job_id: str | None = None
    model: str | None = None
    cost_usd: float = 0.0
    input_summary: str = ""
    output_summary: str = ""
