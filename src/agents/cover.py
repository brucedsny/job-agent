"""Cover letter (Opus), always truthful: runs through the anti-fabrication guard."""

from __future__ import annotations

import re

from pydantic import BaseModel

from ..config import Settings
from ..llm import LLMClient
from ..models import CandidateProfile, StructuredJob, TailoredResume
from .tailor import deterministic_unsupported

_SYSTEM = (
    "Write a short cover letter (3 paragraphs), specific to the job and company, in a "
    "direct professional tone. Use ONLY facts from the candidate profile — no invented "
    "metrics, titles, dates or achievements. Connect real experience to the job's needs."
)


class CoverOutput(BaseModel):
    text: str


def generate_cover_letter(job: StructuredJob, profile: CandidateProfile, resume: TailoredResume,
                          llm: LLMClient, settings: Settings) -> tuple[str, list[str], float]:
    """Returns (text, unsupported_sentences, cost_usd)."""
    user = (f"Candidate: {profile.contact.name}\nSummary: {profile.summary}\n"
            f"Skills: {', '.join(profile.skill_names())}\nHighlights: {resume.headline}\n\n"
            f"Job: {job.title} @ {job.company}\nMust-haves: {', '.join(job.must_haves) or '—'}\n")
    res = llm.structured(settings.model_for("cover"), CoverOutput, _SYSTEM, user)
    text = res.value.text
    corpus = profile.fact_corpus()
    flagged = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text)
               if deterministic_unsupported(s, corpus)]
    return text, flagged, res.cost_usd
