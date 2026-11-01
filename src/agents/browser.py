"""Agent 7c — Browser automation, behind Gate C (explicit per-job consent).

Fills known fields (or LLM-mapped fields), takes a screenshot for human review
and returns NEEDS_MANUAL. Clicking submit additionally requires
`browser_auto_submit=True`. Respect site ToS; never bypass captchas.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ..config import Settings
from ..models import ApplicationDraft, ApplyMode, CandidateProfile, StructuredJob, SubmissionResult

_FIELD_SELECTORS: dict[str, list[str]] = {
    "first_name": ["input[name*='first']", "input[id*='first']"],
    "last_name": ["input[name*='last']", "input[id*='last']"],
    "email": ["input[type='email']", "input[name*='email']"],
    "phone": ["input[type='tel']", "input[name*='phone']"],
}


class BrowserConsentRequired(RuntimeError):
    """Browser automation attempted without Gate C consent."""


class _FieldMapping(BaseModel):
    selector: str
    value: str


class _FieldMap(BaseModel):
    mappings: list[_FieldMapping] = Field(default_factory=list)


def llm_map_fields(fields: list[dict], profile: CandidateProfile, llm, settings) -> dict[str, str]:
    """Map form field descriptors to REAL profile values. Unknown -> omitted."""
    if not fields:
        return {}
    system = ("Map job application form fields to the candidate's REAL data. Use only true "
              "profile values; if there is no data, omit the field. Never invent.")
    c = profile.contact
    user = (f"Profile: name={c.name}, email={c.email}, phone={c.phone or ''}, "
            f"location={c.location or ''}\nFields (json): {fields}")
    res = llm.structured(settings.model_for("assembly"), _FieldMap, system, user)
    return {m.selector: m.value for m in res.value.mappings if m.value}


def submit_via_browser(job: StructuredJob, profile: CandidateProfile, draft: ApplicationDraft,
                       settings: Settings, *, consent: bool, llm=None) -> SubmissionResult:
    if not (settings.gate_c_enabled and consent):
        raise BrowserConsentRequired(
            "Gate C: browser automation needs explicit consent (gate_c_enabled and consent).")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        return SubmissionResult(job_id=job.lead_id, mode=ApplyMode.BROWSER, success=False,
                                error=f"Playwright not installed: {exc}")

    names = profile.contact.name.split()
    values = {"first_name": names[0], "last_name": " ".join(names[1:]) or names[0],
              "email": profile.contact.email, "phone": profile.contact.phone or ""}
    shot = settings.output_dir / f"{job.lead_id}_apply.png"
    pdf = Path(draft.resume_pdf_path)

    try:  # pragma: no cover (needs a real browser)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.browser_headless)
            page = browser.new_page()
            page.goto(job.apply_target or "", wait_until="domcontentloaded")

            mapped = False
            if llm is not None:
                descriptors = [{
                    "selector": el.get_attribute("name") or el.get_attribute("id") or "",
                    "label": el.get_attribute("aria-label") or el.get_attribute("placeholder") or "",
                    "type": el.get_attribute("type") or "text",
                } for el in page.query_selector_all("input, textarea")]
                try:
                    for sel, val in llm_map_fields([d for d in descriptors if d["selector"]],
                                                   profile, llm, settings).items():
                        el = page.query_selector(f"[name='{sel}'], [id='{sel}']")
                        if el:
                            el.fill(val)
                    mapped = True
                except Exception:  # noqa: BLE001 — fall back to deterministic
                    mapped = False
            if not mapped:
                for field, selectors in _FIELD_SELECTORS.items():
                    for sel in selectors:
                        el = page.query_selector(sel)
                        if el and values.get(field):
                            el.fill(values[field])
                            break

            if pdf.exists():
                file_input = page.query_selector("input[type='file']")
                if file_input:
                    file_input.set_input_files(str(pdf))
            page.screenshot(path=str(shot), full_page=True)

            if settings.browser_auto_submit:
                btn = page.query_selector("button[type='submit'], input[type='submit']")
                if btn:
                    btn.click()
                    page.wait_for_load_state("networkidle")
                    browser.close()
                    return SubmissionResult(job_id=job.lead_id, mode=ApplyMode.BROWSER, success=True,
                                            confirmation=f"Form submitted via browser. Screenshot: {shot}")
            browser.close()
    except Exception as exc:  # pragma: no cover
        return SubmissionResult(job_id=job.lead_id, mode=ApplyMode.BROWSER, success=False,
                                error=f"Browser failure: {exc}")

    return SubmissionResult(job_id=job.lead_id, mode=ApplyMode.BROWSER, success=False,
                            error=f"Form filled (manual submit). Review screenshot: {shot}")
