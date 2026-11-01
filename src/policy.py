"""Rules engine for autopilot PREPARATION (never submission) + kill-switch."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .config import Settings
from .models import FitAssessment, StructuredJob


class PolicyDecision(BaseModel):
    passes: bool
    reasons: list[str] = Field(default_factory=list)
    priority: int = 0


class KillSwitchEngaged(RuntimeError):
    """Kill-switch is on: no external/LLM action may run."""


def is_killed(settings: Settings) -> bool:
    return bool(settings.kill_switch) or settings.stop_file.exists()


def evaluate_policy(job: StructuredJob, fit: FitAssessment, settings: Settings,
                    has_open_questions: bool = False) -> PolicyDecision:
    reasons: list[str] = []
    if fit.score < settings.policy_min_score:
        reasons.append(f"score {fit.score} < min {settings.policy_min_score}")
    if settings.policy_require_full_must and fit.missing_must:
        reasons.append(f"missing must-haves: {', '.join(fit.missing_must)}")
    if settings.policy_block_open_questions and has_open_questions:
        reasons.append("has open questions (needs human review)")

    company = (job.company or "").lower()
    if any(b.lower() in company for b in settings.policy_company_blocklist):
        reasons.append("company is blocklisted")
    if settings.policy_company_allowlist and not any(
        a.lower() in company for a in settings.policy_company_allowlist
    ):
        reasons.append("company not in allowlist")
    if (settings.policy_salary_floor is not None and job.salary_max is not None
            and job.salary_max < settings.policy_salary_floor):
        reasons.append(f"salary max {job.salary_max} < floor {settings.policy_salary_floor}")

    return PolicyDecision(passes=not reasons, reasons=reasons, priority=fit.score)
