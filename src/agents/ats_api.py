"""ATS API submission. Real Greenhouse Job Board API (behind a credential).

Lever/Ashby are reserved interfaces that fall back to NEEDS_MANUAL. Only ever
runs after human approval (Gate B is enforced by the caller).
"""

from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Callable

from ..config import Settings
from ..models import ApplicationDraft, ApplyMode, CandidateProfile, StructuredJob, SubmissionResult

_GH_REF = re.compile(r"greenhouse\.io/(?:embed/job_app\?for=)?([^/?&]+)(?:/jobs/|&token=)(\d+)")

# http_post(url, headers, data, files) -> object with .status_code and .text
HttpPost = Callable[[str, dict, dict, dict | None], object]


def parse_greenhouse_ref(url: str) -> tuple[str, str] | None:
    m = _GH_REF.search(url or "")
    return (m.group(1), m.group(2)) if m else None


def submit_greenhouse(job: StructuredJob, profile: CandidateProfile, draft: ApplicationDraft,
                      api_key: str, http_post: HttpPost | None = None) -> SubmissionResult:
    ref = parse_greenhouse_ref(job.apply_target or "")
    if ref is None:
        return SubmissionResult(job_id=job.lead_id, mode=ApplyMode.API, success=False,
                                error="Could not parse board/job id from the Greenhouse URL.")
    board, job_id = ref
    names = profile.contact.name.split()
    data = {"first_name": names[0], "last_name": " ".join(names[1:]) or names[0],
            "email": profile.contact.email}
    if profile.contact.phone:
        data["phone"] = profile.contact.phone
    pdf = Path(draft.resume_pdf_path)
    files = {"resume": (pdf.name, pdf.read_bytes(), "application/pdf")} if pdf.exists() else None
    token = base64.b64encode(f"{api_key}:".encode()).decode()

    resp = (http_post or _default_post)(
        f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}",
        {"Authorization": f"Basic {token}"}, data, files)
    code = getattr(resp, "status_code", 0)
    if code in (200, 201):
        return SubmissionResult(job_id=job.lead_id, mode=ApplyMode.API, success=True,
                                confirmation=f"Greenhouse accepted the application ({board}/{job_id}).")
    return SubmissionResult(job_id=job.lead_id, mode=ApplyMode.API, success=False,
                            error=f"Greenhouse returned {code}: {getattr(resp, 'text', '')[:200]}")


def submit_via_ats(job: StructuredJob, profile: CandidateProfile, draft: ApplicationDraft,
                   settings: Settings, http_post: HttpPost | None = None) -> SubmissionResult | None:
    """None means no viable API path (caller falls back to manual)."""
    if "greenhouse.io" in (job.apply_target or "").lower() and settings.greenhouse_api_key:
        return submit_greenhouse(job, profile, draft, settings.greenhouse_api_key, http_post)
    return None


def _default_post(url, headers, data, files):  # pragma: no cover (network)
    import httpx

    return httpx.post(url, headers=headers, data=data, files=files, timeout=60)
