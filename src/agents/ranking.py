"""Agent 3 — Fit Ranking: realistic probability of getting an interview."""

from __future__ import annotations

from ..config import Settings
from ..llm import LLMClient
from ..models import CandidateProfile, FitAssessment, FitResult, StructuredJob

_SYSTEM = (
    "You are a senior technical recruiter estimating the REAL probability that this "
    "candidate gets an interview — not keyword similarity. Weigh met vs. missing "
    "must-haves, seniority alignment, relevant gaps and typical competitiveness. Be "
    "calibrated: missing must-haves lower the probability. interview_probability in "
    "[0,1]; score = round(prob*100)."
)


def _profile_brief(profile: CandidateProfile) -> str:
    lines = [f"Summary: {profile.summary}", f"Skills: {', '.join(profile.skill_names())}"]
    for e in profile.experiences:
        lines.append(f"- {e.title} @ {e.company} ({e.start}–{e.end or 'present'})")
        lines += [f"    • {b}" for b in e.bullets[:4]]
    lines += [f"- Education: {ed.degree} {ed.field or ''} @ {ed.institution}" for ed in profile.education]
    return "\n".join(lines)


def assess_fit(job: StructuredJob, profile: CandidateProfile, llm: LLMClient,
               settings: Settings) -> tuple[FitAssessment, float]:
    user = (
        "=== CANDIDATE ===\n" + _profile_brief(profile) + "\n\n=== JOB ===\n"
        f"Title: {job.title} | Company: {job.company} | Seniority: {job.seniority.value}\n"
        f"Must-haves: {', '.join(job.must_haves) or '—'}\n"
        f"Nice-to-haves: {', '.join(job.nice_to_haves) or '—'}\n"
        f"Responsibilities: {', '.join(job.responsibilities[:8]) or '—'}\n"
    )
    result = llm.structured(settings.model_for("fit"), FitResult, _SYSTEM, user)
    r: FitResult = result.value
    score = max(0, min(100, int(r.score)))
    return FitAssessment(
        job_id=job.lead_id, interview_probability=max(0.0, min(1.0, r.interview_probability)),
        score=score, matched_must=r.matched_must, missing_must=r.missing_must, gaps=r.gaps,
        rationale=r.rationale, recommended=score >= settings.fit_threshold,
    ), result.cost_usd
