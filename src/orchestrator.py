"""Orchestrator: chains the agents, persists status, audits cost.

Every step is idempotent. Automatic runs STOP at Gate B (pending_approval);
submitting always requires explicit human approval.
"""

from __future__ import annotations

from typing import Callable

from . import learning, policy
from .agents import assembly, discovery, document, extraction, ranking, tailor
from .agents.submission import submit as submit_application
from .config import Settings, get_settings
from .crm.repository import CRM
from .llm import LLMClient, SpendCapExceeded
from .models import AuditEntry, CandidateProfile, JobStatus, SubmissionResult
from .obs import get_logger
from .policy import KillSwitchEngaged

_log = get_logger()


class Orchestrator:
    def __init__(self, crm: CRM, profile: CandidateProfile, settings: Settings | None = None,
                 llm: LLMClient | None = None, fetcher: Callable[[str], str] | None = None,
                 fetch_json: Callable[[str], object] | None = None) -> None:
        self.crm = crm
        self.profile = profile
        self.settings = settings or get_settings()
        self.llm = llm or LLMClient(self.settings)
        self.fetcher = fetcher
        self.fetch_json = fetch_json

    # -- helpers -----------------------------------------------------------
    def _audit(self, action: str, job_id: str | None, model: str | None, cost: float, out: str) -> None:
        self.crm.audit(AuditEntry(action=action, job_id=job_id, model=model, cost_usd=cost,
                                  output_summary=out[:300]))

    def _pdf_path(self, job_id: str) -> str:
        return str(self.settings.output_dir / f"{job_id}.pdf")

    def _check_kill(self) -> None:
        if policy.is_killed(self.settings):
            raise KillSwitchEngaged("Kill-switch on (kill_switch=True or data/STOP exists).")

    def _require(self, value, msg: str):
        if value is None:
            raise ValueError(msg)
        return value

    # -- 1 discovery -------------------------------------------------------
    def _ingest(self, leads, action: str) -> int:
        added = sum(int(self.crm.add_lead(ld, discovery.canonicalize_url(ld.url))) for ld in leads)
        self._audit(action, None, None, 0.0, f"found={len(leads)} added={added}")
        return added

    def discover_url(self, url: str, title: str | None = None) -> int:
        return self._ingest([discovery.discover_from_url(url, title)], "discover_url")

    def discover_all(self, query: str | None = None) -> int:
        self._check_kill()
        return self._ingest(discovery.discover_all(self.settings, query, self.fetch_json), "discover_all")

    # -- 2 extraction ------------------------------------------------------
    def extract(self, job_id: str) -> None:
        self._check_kill()
        lead = self._require(self.crm.get_lead(job_id), f"Lead {job_id} not found.")
        text = extraction.fetch_text(lead.url, self.fetcher)
        job, cost = extraction.extract_job(lead, text, self.llm, self.settings)
        self.crm.save_job(job)
        self.crm.set_status(job_id, JobStatus.EXTRACTED)
        self._audit("extract", job_id, self.settings.model_for("extraction"), cost,
                    f"{job.title} @ {job.company}")

    # -- 3 ranking (+ funnel learning) ------------------------------------
    def rank(self, job_id: str) -> None:
        self._check_kill()
        job = self._require(self.crm.get_job(job_id), f"Job {job_id} not extracted.")
        fit, cost = ranking.assess_fit(job, self.profile, self.llm, self.settings)
        delta, note = learning.score_adjustment(job, fit, self.crm)
        if delta:
            fit.score = max(0, min(100, fit.score + delta))
            fit.recommended = fit.score >= self.settings.fit_threshold
            fit.rationale = f"{fit.rationale}\n[{note}]"
        self.crm.save_fit(fit)
        self.crm.set_status(job_id, JobStatus.RANKED if fit.recommended else JobStatus.ICEBOX)
        self._audit("rank", job_id, self.settings.model_for("fit"), cost,
                    f"score={fit.score} p={fit.interview_probability:.2f} adj={delta:+d}")

    def select(self, job_id: str) -> None:  # Gate A
        self.crm.set_status(job_id, JobStatus.SELECTED)
        self._audit("select", job_id, None, 0.0, "gate_a: selected")

    # -- 4 tailoring -------------------------------------------------------
    def tailor(self, job_id: str) -> None:
        self._check_kill()
        job = self._require(self.crm.get_job(job_id), f"Job {job_id} not extracted.")
        resume, cost = tailor.tailor_resume(job, self.profile, self.llm, self.settings)
        self.crm.save_tailored(resume)
        self.crm.set_status(job_id, JobStatus.TAILORED)
        self._audit("tailor", job_id, self.settings.model_for("tailor"), cost,
                    f"flags={len(resume.flagged_unsupported)}")

    # -- 5 document --------------------------------------------------------
    def document(self, job_id: str) -> str:
        self._check_kill()
        resume = self._require(self.crm.get_tailored(job_id), f"No tailored resume for {job_id}.")
        out = self._pdf_path(job_id)
        engine = document.render_pdf(resume, out)
        report = document.validate_ats(out)
        self.crm.set_status(job_id, JobStatus.DOCUMENT_READY)
        self._audit("document", job_id, None, 0.0, f"engine={engine} ats_ok={report.passed}")
        return out

    # -- 6 assembly --------------------------------------------------------
    def assemble(self, job_id: str, screening_questions: list[str] | None = None,
                 with_cover_letter: bool | None = None) -> None:
        self._check_kill()
        job = self._require(self.crm.get_job(job_id), f"Job {job_id} not extracted.")
        resume = self._require(self.crm.get_tailored(job_id), f"No tailored resume for {job_id}.")
        if with_cover_letter is None:
            with_cover_letter = self.settings.cover_letter_default
        pdf = self._pdf_path(job_id)
        draft, cost = assembly.assemble(
            job, resume, pdf, document.validate_ats(pdf), self.profile,
            screening_questions=screening_questions, with_cover_letter=with_cover_letter,
            llm=self.llm, settings=self.settings)
        self.crm.save_draft(draft)
        self.crm.set_status(job_id, JobStatus.PENDING_APPROVAL)
        self._audit("assemble", job_id, self.settings.model_for("assembly"), cost,
                    f"blocking={len(draft.blocking_issues)}")

    # -- Gate B ------------------------------------------------------------
    def approve(self, job_id: str) -> None:
        draft = self._require(self.crm.get_draft(job_id), f"No draft for {job_id}.")
        if draft.blocking_issues:
            raise ValueError("Cannot approve: blocking issues — " + "; ".join(draft.blocking_issues))
        draft.status = JobStatus.APPROVED
        self.crm.save_draft(draft)
        self.crm.set_status(job_id, JobStatus.APPROVED)
        self._audit("approve", job_id, None, 0.0, "gate_b: approved by human")

    def reject(self, job_id: str) -> None:
        draft = self.crm.get_draft(job_id)
        if draft:
            draft.status = JobStatus.REJECTED
            self.crm.save_draft(draft)
        self.crm.set_status(job_id, JobStatus.REJECTED)
        self._audit("reject", job_id, None, 0.0, "gate_b: rejected")

    def approve_all(self) -> list[str]:
        """Human-triggered batch approval of drafts WITHOUT blocking issues."""
        approved = []
        for lead, _ in self.crm.list_leads(JobStatus.PENDING_APPROVAL):
            draft = self.crm.get_draft(lead.id)
            if draft and not draft.blocking_issues:
                self.approve(lead.id)
                approved.append(lead.id)
        return approved

    # -- 7 submission ------------------------------------------------------
    def submit(self, job_id: str, consent: bool = False) -> SubmissionResult:
        self._check_kill()
        draft = self._require(self.crm.get_draft(job_id), f"No draft for {job_id}.")
        job = self._require(self.crm.get_job(job_id), f"Job {job_id} not extracted.")
        result = submit_application(
            draft, job, self.profile, self.settings,
            submissions_today=self.crm.submissions_today(),
            company_count=self.crm.submissions_for_company(job.company),
            consent=consent, llm=self.llm)
        self.crm.save_submission(result)
        if result.success:
            self.crm.record_outcome(job_id, "applied")
            status = JobStatus.SUBMITTED
        elif "manual" in (result.error or "").lower():
            status = JobStatus.NEEDS_MANUAL
        else:
            status = JobStatus.FAILED
        self.crm.set_status(job_id, status)
        self._audit("submit", job_id, None, 0.0, result.confirmation or result.error or "")
        return result

    def record_outcome(self, job_id: str, outcome: str) -> None:
        self.crm.record_outcome(job_id, outcome)
        self._audit("outcome", job_id, None, 0.0, outcome)

    # -- pipelines ---------------------------------------------------------
    def run_until_approval(self, job_id: str, auto_select: bool = True) -> JobStatus:
        """Runs 2->6 and STOPS at pending_approval (never submits)."""
        self.extract(job_id)
        self.rank(job_id)
        if self.crm.get_status(job_id) == JobStatus.ICEBOX:
            return JobStatus.ICEBOX
        if auto_select:
            self.select(job_id)
        self.tailor(job_id)
        self.document(job_id)
        self.assemble(job_id)
        return self.crm.get_status(job_id) or JobStatus.PENDING_APPROVAL

    def _batch(self, status: JobStatus, step) -> dict[str, int]:
        done, stopped = 0, False
        for lead, _ in self.crm.list_leads(status):
            try:
                step(lead.id)
                done += 1
            except SpendCapExceeded:
                stopped = True
                break
        return {"processed": done, "stopped_by_spend_cap": int(stopped)}

    def extract_all(self) -> dict[str, int]:
        return self._batch(JobStatus.DISCOVERED, self.extract)

    def rank_all(self) -> dict[str, int]:
        return self._batch(JobStatus.EXTRACTED, self.rank)

    def run_all(self) -> dict[str, int]:
        return self._batch(JobStatus.DISCOVERED, self.run_until_approval)

    def autopilot(self, query: str | None = None, max_n: int | None = None) -> dict:
        """Discover, evaluate by policy and PREPARE high-fit applications up to
        Gate B — automatically, but NEVER submits."""
        self._check_kill()
        max_n = max_n or self.settings.autopilot_max
        self.discover_all(query)
        prepared: list[str] = []
        skipped: list[dict] = []
        stopped: str | None = None
        for count, (lead, _) in enumerate(self.crm.list_leads(JobStatus.DISCOVERED)):
            if count >= max_n:
                break
            try:
                self.extract(lead.id)
                self.rank(lead.id)
                decision = policy.evaluate_policy(self.crm.get_job(lead.id),
                                                  self.crm.get_fit(lead.id), self.settings)
                if not decision.passes:
                    skipped.append({"id": lead.id, "reasons": decision.reasons})
                    continue
                self.select(lead.id)
                self.tailor(lead.id)
                self.document(lead.id)
                self.assemble(lead.id)
                prepared.append(lead.id)
            except SpendCapExceeded:
                stopped = "spend_cap"
                break
            except KillSwitchEngaged:
                stopped = "kill_switch"
                break
            except Exception as exc:  # noqa: BLE001 — resilience: skip this job
                _log.warning("autopilot: %s failed: %s", lead.id, exc)
                skipped.append({"id": lead.id, "reasons": [str(exc)]})

        prepared.sort(key=lambda jid: self.crm.get_fit(jid).score, reverse=True)
        self._audit("autopilot", None, None, 0.0,
                    f"prepared={len(prepared)} skipped={len(skipped)} stopped={stopped}")
        return {"prepared": prepared, "skipped": skipped, "stopped": stopped}
