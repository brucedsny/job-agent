"""Funnel learning: callback rates by bucket -> small ranking adjustment.

Adjusts PRIORITIZATION only; never touches resume facts.
"""

from __future__ import annotations

from .crm.repository import CRM
from .models import FitAssessment, StructuredJob

POSITIVE = {"callback", "interview", "offer"}


def _score_bucket(score: int) -> str:
    if score >= 90:
        return "90-100"
    if score >= 75:
        return "75-89"
    if score >= 60:
        return "60-74"
    return "0-59"


def _per_job(crm: CRM) -> dict[str, set[str]]:
    per_job: dict[str, set[str]] = {}
    for job_id, outcome in crm.list_outcomes():
        per_job.setdefault(job_id, set()).add(outcome)
    return per_job


def _stored_buckets(crm: CRM, job_id: str) -> dict[str, str]:
    lead, job, fit = crm.get_lead(job_id), crm.get_job(job_id), crm.get_fit(job_id)
    buckets: dict[str, str] = {}
    if lead:
        buckets["source"] = lead.source.split(":")[0]
    if job:
        buckets["seniority"] = job.seniority.value
    if fit:
        buckets["score"] = _score_bucket(fit.score)
    return buckets


def callback_rates(crm: CRM) -> dict[str, dict[str, float]]:
    """'dim:value' -> {applied, positive, rate}."""
    agg: dict[str, dict[str, float]] = {}
    for job_id, outcomes in _per_job(crm).items():
        positive = bool(outcomes & POSITIVE)
        for dim, val in _stored_buckets(crm, job_id).items():
            a = agg.setdefault(f"{dim}:{val}", {"applied": 0, "positive": 0, "rate": 0.0})
            a["applied"] += 1
            a["positive"] += int(positive)
    for a in agg.values():
        a["rate"] = a["positive"] / a["applied"] if a["applied"] else 0.0
    return agg


def score_adjustment(job: StructuredJob, fit: FitAssessment, crm: CRM) -> tuple[int, str]:
    """Bounded (+/-10) score delta from history. Returns (delta, note)."""
    per_job = _per_job(crm)
    total = len(per_job)
    if total < 3:
        return 0, "not enough history for adjustment"
    base = sum(1 for o in per_job.values() if o & POSITIVE) / total

    rates = callback_rates(crm)
    live = {"seniority": job.seniority.value, "score": _score_bucket(fit.score)}
    delta, notes = 0, []
    for dim, val in live.items():
        key = f"{dim}:{val}"
        bucket = rates.get(key)
        if bucket and bucket["applied"] >= 3:
            d = max(-5, min(5, round((bucket["rate"] - base) * 20)))
            if d:
                delta += d
                notes.append(f"{key} {bucket['rate']:.0%}({d:+d})")
    delta = max(-10, min(10, delta))
    return delta, "funnel adjustment: " + (", ".join(notes) if notes else "neutral")
