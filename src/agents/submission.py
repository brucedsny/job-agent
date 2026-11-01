"""Agent 7 — Submission, only AFTER human approval (Gate B).

Never auto-applies: requires draft.status == APPROVED and no blocking issues.
Layers: ATS API -> email -> browser (Gate C) -> manual.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from ..config import GATE_B_ALWAYS_REQUIRED, Settings
from ..models import ApplicationDraft, ApplyMode, CandidateProfile, JobStatus, StructuredJob, SubmissionResult
from . import ats_api, browser


class SubmissionBlocked(RuntimeError):
    """Submission without human approval, with blocking issues, or over a cap."""


def _check_gate_b(draft: ApplicationDraft) -> None:
    if GATE_B_ALWAYS_REQUIRED and draft.status != JobStatus.APPROVED:
        raise SubmissionBlocked("Gate B: application not approved by a human (no auto-apply).")
    if draft.blocking_issues:
        raise SubmissionBlocked("Draft has blocking issues: " + "; ".join(draft.blocking_issues))


def _check_caps(job: StructuredJob, today: int, company_count: int, settings: Settings) -> None:
    if today >= settings.daily_application_cap:
        raise SubmissionBlocked(f"Daily application cap reached ({settings.daily_application_cap}).")
    if company_count >= settings.per_company_cap:
        raise SubmissionBlocked(f"Per-company cap reached for {job.company}.")


def _manual(job: StructuredJob, mode: ApplyMode, why: str) -> SubmissionResult:
    return SubmissionResult(job_id=job.lead_id, mode=mode, success=False,
                            error=f"{why} Apply manually at: {job.apply_target or job.lead_id}")


def submit(draft: ApplicationDraft, job: StructuredJob, profile: CandidateProfile,
           settings: Settings, *, submissions_today: int = 0, company_count: int = 0,
           consent: bool = False, llm=None) -> SubmissionResult:
    _check_gate_b(draft)
    _check_caps(job, submissions_today, company_count, settings)

    if job.apply_mode == ApplyMode.EMAIL and job.apply_target:
        return _submit_email(draft, job, profile, settings)
    if job.apply_mode == ApplyMode.API:
        result = ats_api.submit_via_ats(job, profile, draft, settings)
        return result or _manual(job, ApplyMode.API, "ATS API not configured for this source (manual).")
    if job.apply_mode == ApplyMode.BROWSER:
        if settings.gate_c_enabled and consent:
            return browser.submit_via_browser(job, profile, draft, settings, consent=True, llm=llm)
        return _manual(job, ApplyMode.BROWSER, "Browser mode needs Gate C consent (manual).")
    return _manual(job, job.apply_mode, "Unknown apply mode (manual).")


def _submit_email(draft: ApplicationDraft, job: StructuredJob, profile: CandidateProfile,
                  settings: Settings) -> SubmissionResult:
    msg = EmailMessage()
    msg["Subject"] = f"Candidatura — {job.title}"
    msg["From"] = settings.smtp_from or profile.contact.email
    msg["To"] = job.apply_target
    msg.set_content(
        f"Olá,\n\nSegue minha candidatura para {job.title} ({job.company}).\n"
        f"{draft.cover_letter or 'Currículo em anexo.'}\n\n"
        f"Atenciosamente,\n{profile.contact.name}\n{profile.contact.email}")
    pdf = Path(draft.resume_pdf_path)
    if pdf.exists():
        msg.add_attachment(pdf.read_bytes(), maintype="application", subtype="pdf", filename=pdf.name)

    if not settings.smtp_host:
        out = settings.outbox_dir / f"{job.lead_id}.eml"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(bytes(msg))
        return SubmissionResult(job_id=job.lead_id, mode=ApplyMode.EMAIL, success=False,
                                error=f"SMTP not configured. Email saved for manual sending: {out}")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password or "")
            server.send_message(msg)
    except Exception as exc:  # noqa: BLE001
        return SubmissionResult(job_id=job.lead_id, mode=ApplyMode.EMAIL, success=False,
                                error=f"SMTP failure: {exc}")
    return SubmissionResult(job_id=job.lead_id, mode=ApplyMode.EMAIL, success=True,
                            confirmation=f"Email sent to {job.apply_target}")
