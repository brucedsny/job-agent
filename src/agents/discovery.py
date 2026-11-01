"""Agent 1 — Discovery: manual URL, Greenhouse, Lever and Ashby job boards.

Parsers are pure (testable offline); HTTP fetchers are injectable.
"""

from __future__ import annotations

import html as html_lib
from typing import Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ..models import JobLead

_TRACKING_PREFIXES = ("utm_", "gh_", "gclid", "fbclid", "ref", "source")

GREENHOUSE_JOBS_URL = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
LEVER_POSTINGS_URL = "https://api.lever.co/v0/postings/{company}?mode=json"
ASHBY_BOARD_URL = "https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true"

FetchJson = Callable[[str], object]


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query)
             if not any(k.lower().startswith(p) for p in _TRACKING_PREFIXES)]
    return urlunsplit(((parts.scheme or "https").lower(), parts.netloc.lower(),
                       parts.path.rstrip("/") or "/", urlencode(sorted(query)), ""))


def discover_from_url(url: str, title: str | None = None) -> JobLead:
    return JobLead(source="manual", url=url, title=title)


def _lead(source: str, company: str, title: str, url: str, content: str, ext_id) -> JobLead:
    return JobLead(source=source, url=url, title=title, company=company,
                   content_hash=JobLead.hash_content(title + content + str(ext_id)),
                   raw_snippet=content[:280] or None)


def _matches(title: str, query: str | None) -> bool:
    q = (query or "").lower().strip()
    return not q or q in title.lower()


def parse_greenhouse_jobs(payload: dict, board: str, query: str | None = None) -> list[JobLead]:
    return [
        _lead(f"greenhouse:{board}", board, j.get("title") or "", j.get("absolute_url", ""),
              html_lib.unescape(j.get("content") or ""), j.get("id", ""))
        for j in payload.get("jobs", []) if _matches(j.get("title") or "", query)
    ]


def parse_lever_postings(postings: list, company: str, query: str | None = None) -> list[JobLead]:
    return [
        _lead(f"lever:{company}", company, p.get("text") or "",
              p.get("hostedUrl") or p.get("applyUrl") or "",
              p.get("descriptionPlain") or html_lib.unescape(p.get("description") or ""),
              p.get("id", ""))
        for p in postings if _matches(p.get("text") or "", query)
    ]


def parse_ashby_jobs(payload: dict, board: str, query: str | None = None) -> list[JobLead]:
    return [
        _lead(f"ashby:{board}", board, j.get("title") or "",
              j.get("jobUrl") or j.get("applyUrl") or "",
              j.get("descriptionPlain") or html_lib.unescape(j.get("descriptionHtml") or ""),
              j.get("id", ""))
        for j in payload.get("jobs", []) if _matches(j.get("title") or "", query)
    ]


def discover_greenhouse(board: str, query: str | None = None,
                        fetch_json: FetchJson | None = None) -> list[JobLead]:
    data = (fetch_json or _default_fetch_json)(GREENHOUSE_JOBS_URL.format(board=board))
    return parse_greenhouse_jobs(data if isinstance(data, dict) else {}, board, query)


def discover_lever(company: str, query: str | None = None,
                   fetch_json: FetchJson | None = None) -> list[JobLead]:
    data = (fetch_json or _default_fetch_json)(LEVER_POSTINGS_URL.format(company=company))
    return parse_lever_postings(data if isinstance(data, list) else [], company, query)


def discover_ashby(board: str, query: str | None = None,
                   fetch_json: FetchJson | None = None) -> list[JobLead]:
    data = (fetch_json or _default_fetch_json)(ASHBY_BOARD_URL.format(board=board))
    return parse_ashby_jobs(data if isinstance(data, dict) else {}, board, query)


def discover_all(settings, query: str | None = None,
                 fetch_json: FetchJson | None = None) -> list[JobLead]:
    leads: list[JobLead] = []
    for board in settings.greenhouse_boards:
        leads += discover_greenhouse(board, query, fetch_json)
    for company in settings.lever_companies:
        leads += discover_lever(company, query, fetch_json)
    for board in settings.ashby_boards:
        leads += discover_ashby(board, query, fetch_json)
    return leads


def _default_fetch_json(url: str):  # pragma: no cover (network)
    import httpx

    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return resp.json()
