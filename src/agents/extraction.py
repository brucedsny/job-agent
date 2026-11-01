"""Agent 2 — Extraction: fetch the job description and structure it."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Callable

from ..config import Settings
from ..llm import LLMClient
from ..models import ApplyMode, JobExtraction, JobLead, StructuredJob

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_MAILTO_RE = re.compile(r"mailto:([^\s\"'>]+)")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True
        if tag in ("p", "br", "li", "div", "h1", "h2", "h3", "tr"):
            self._chunks.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip and data.strip():
            self._chunks.append(data)

    def text(self) -> str:
        joined = re.sub(r"[ \t]+", " ", " ".join(self._chunks))
        return re.sub(r"[ \t]*\n[ \t]*", "\n", joined).strip()


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.text()


def fetch_text(url: str, fetch: Callable[[str], str] | None = None) -> str:
    raw = (fetch or _default_fetch)(url)
    return html_to_text(raw) if "<" in raw and ">" in raw else raw


def _default_fetch(url: str) -> str:  # pragma: no cover (network)
    import httpx

    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def detect_apply_mode(lead: JobLead, text: str) -> tuple[ApplyMode, str | None]:
    mailto = _MAILTO_RE.search(f"{lead.url}\n{text}")
    if mailto:
        return ApplyMode.EMAIL, mailto.group(1)
    low = lead.url.lower()
    if any(h in low for h in ("greenhouse.io", "lever.co", "ashbyhq.com")):
        return ApplyMode.API, lead.url
    email = _EMAIL_RE.search(text)
    if email and ("send" in text.lower() or "envie" in text.lower()):
        return ApplyMode.EMAIL, email.group(0)
    return ApplyMode.BROWSER, lead.url


_SYSTEM = (
    "You extract structured data from job descriptions. Be faithful to the text: do NOT "
    "invent requirements, salary or seniority. Leave missing fields empty/UNKNOWN. "
    "Separate mandatory requirements (must) from nice-to-haves."
)


def extract_job(lead: JobLead, text: str, llm: LLMClient,
                settings: Settings) -> tuple[StructuredJob, float]:
    model = settings.model_for(
        "extraction_heavy" if len(text) > settings.extraction_heavy_chars else "extraction")
    user = (f"URL: {lead.url}\nCompany (guess): {lead.company or ''}\n\n"
            f"=== JOB DESCRIPTION ===\n{text[:30000]}")
    result = llm.structured(model, JobExtraction, _SYSTEM, user)
    ext: JobExtraction = result.value
    mode, target = detect_apply_mode(lead, text)
    job = StructuredJob(
        lead_id=lead.id, title=ext.title or (lead.title or "Job"),
        company=ext.company or (lead.company or "Company"), location=ext.location,
        work_model=ext.work_model, seniority=ext.seniority, must_haves=ext.must_haves,
        nice_to_haves=ext.nice_to_haves, responsibilities=ext.responsibilities,
        salary_min=ext.salary_min, salary_max=ext.salary_max,
        salary_currency=ext.salary_currency, apply_mode=mode, apply_target=target,
        raw_text=text[:30000],
    )
    return job, result.cost_usd
