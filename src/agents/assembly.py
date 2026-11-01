"""Agent 6 — Application Assembly: builds the package for Gate B.

Collects PDF, optional screening answers and cover letter, a checklist, and
`blocking_issues` (unsupported claims, failed ATS, missing PDF...). A blocked
draft cannot be approved until a human fixes it.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from ..config import Settings
from ..llm import LLMClient
from ..models import (
    ApplicationDraft,
    CandidateProfile,
    JobStatus,
    ScreeningQA,
    StructuredJob,
    TailoredResume,
)
from . import cover
from .document import AtsReport
from .tailor import deterministic_unsupported

_SCREEN_SYSTEM = (
    "Answer the screening question concisely and truthfully, using only facts from the "
    "candidate profile. Do not invent experience, numbers or dates."
)


class _Answer(BaseModel):
    answer: str


def _answer_screening(question: str, profile: CandidateProfile, llm: LLMClient,
                      settings: Settings) -> tuple[ScreeningQA, float]:
    user = (f"Profile: {profile.summary}\nSkills: {', '.join(profile.skill_names())}"
            f"\n\nQuestion: {question}")
    res = llm.structured(settings.model_for("assembly"), _Answer, _SCREEN_SYSTEM, user)
    answer = res.value.answer
    grounded = not deterministic_unsupported(answer, profile.fact_corpus())
    return ScreeningQA(question=question, answer=answer, grounded=grounded), res.cost_usd


def assemble(job: StructuredJob, resume: TailoredResume, pdf_path: str | Path, ats: AtsReport,
             profile: CandidateProfile, *, screening_questions: list[str] | None = None,
             with_cover_letter: bool = False, llm: LLMClient | None = None,
             settings: Settings | None = None) -> tuple[ApplicationDraft, float]:
    pdf_path = Path(pdf_path)
    cost = 0.0
    if (screening_questions or with_cover_letter) and (llm is None or settings is None):
        raise ValueError("screening/cover letter require llm and settings")

    screening: list[ScreeningQA] = []
    for q in screening_questions or []:
        qa, c = _answer_screening(q, profile, llm, settings)
        screening.append(qa)
        cost += c

    cover_letter, cover_flagged = None, []
    if with_cover_letter:
        cover_letter, cover_flagged, c = cover.generate_cover_letter(job, profile, resume, llm, settings)
        cost += c

    checklist = [
        f"PDF: {pdf_path.name}",
        f"ATS: {'OK' if ats.passed else 'ISSUES'} ({ats.char_count} chars, "
        f"headings={', '.join(ats.found_headings) or '—'})",
        f"Unsupported resume claims: {len(resume.flagged_unsupported)}",
        f"Apply mode: {job.apply_mode.value} -> {job.apply_target or '—'}",
    ]
    if cover_letter:
        checklist.append("Cover letter generated (review it).")

    blocking: list[str] = []
    if not pdf_path.exists():
        blocking.append("PDF not found.")
    if not ats.passed:
        blocking.append("PDF failed ATS validation: " + "; ".join(ats.issues))
    if resume.has_unsupported:
        blocking.append("Resume has unsupported claims (review in Gate D): "
                        + "; ".join(resume.flagged_unsupported[:5]))
    ungrounded = [qa.question for qa in screening if not qa.grounded]
    if ungrounded:
        blocking.append("Unsupported screening answers: " + "; ".join(ungrounded))
    if cover_flagged:
        blocking.append("Cover letter has unsupported claims: " + "; ".join(cover_flagged[:3]))
    if not profile.contact.email:
        blocking.append("Profile has no contact email.")

    return ApplicationDraft(
        job_id=job.lead_id, resume_pdf_path=str(pdf_path), cover_letter=cover_letter,
        screening=screening, checklist=checklist, blocking_issues=blocking,
        status=JobStatus.PENDING_APPROVAL,
    ), cost
