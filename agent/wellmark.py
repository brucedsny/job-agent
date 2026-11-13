#!/usr/bin/env python3
"""myWellmark document downloader (Wellmark Blue Cross and Blue Shield portal).

Logs into myWellmark with Playwright, reads the claims, EOB list and prior
authorizations that the portal keeps in its own session cache, and downloads
the EOB PDFs and the authorization letters (approvals, denials, SNF
decisions) into --out, plus index.json (date, type, title, status, file) for
the /atualiza skill. Credentials come only from WELLMARK_USER/WELLMARK_PASS.
The output holds patient data: keep it in the scratchpad, never in the repo.

Usage:
    python3 agent/wellmark.py --out DIR [--since YYYY-MM-DD] [--allow-sms] [--headed]

Protocol with the orchestrator (as in mychart.py):
  - <out>/status.json: {"state": starting | loading_portal | logging_in |
    waiting_mfa | mfa_submitted | reading | downloading | done | error |
    blocked, "detail": ..., "mfa_channel": email | sms | unknown}.
  - MFA by e-mail: in state waiting_mfa, write the code (from Gmail) into
    <out>/mfa_code.txt; it is polled for --mfa-timeout seconds and deleted
    once used.
  - MFA by SMS (or an unknown channel) needs the person: the run stops with
    exit 6 unless --allow-sms (someone writes the code into mfa_code.txt) or
    --headed (someone types it in the browser window).
  - CAPTCHA, bot check or any challenge page: the run stops with exit 7 and
    leaves blocked.txt/.png. It is never worked around.

Exit codes: 0 ok, 2 login failed, 3 MFA timeout, 4 network blocked, 5 other,
6 MFA needs SMS or a person, 7 CAPTCHA / bot check / challenge page.

Portal notes (2026-10/11):
- mywellmark.wellmark.com redirects to authentication.wellmark.com:
  #username, #password, Enter. MFA at /authentication/mfa/verify:
  #verificationCode, Enter (clicking VERIFY times out). In 2026-10 the
  account offered only SMS for MFA.
- Logged in, the Angular app keeps claims, eobSummary, preService
  (authorizations with authLetter keys) and claimDenialInfo in
  sessionStorage "cachedMemberInfo" (a one-item list), filled while /claims
  and /coverage/authorizations load. The claims "Download" button and the
  letters dialog answer "Whoops!", so the cache is the source.
- Documents: GET <api>/member-portal-api/v1/document/eob/documentid/<key>
  ?sendPage=false&icn=<icn> and .../document/authorization/documentid/<key>
  ?sendPage=false, with Authorization = the raw JWT in sessionStorage
  "ngx-webstorage|wellmarkjwt" (no "Bearer") and vnd.wellmark.clientappname:
  member-portal. The reply is a short-lived S3/CloudFront link (or the PDF);
  CloudFront wants a Referer from the portal.
- 2026-11: to headless Chromium the portal serves HTML instead of its
  scripts and stays on "Loading". That is a bot check, so the run stops.
"""

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from mychart import find_chromium_executable  # noqa: E402

# Overridable for offline tests against a local mock.
PORTAL = os.environ.get("WELLMARK_PORTAL_URL", "https://mywellmark.wellmark.com").rstrip("/")
API = os.environ.get("WELLMARK_API_URL", "https://apigw.wellmark.com").rstrip("/")

NAV_MS = 45_000
PORTAL_LOAD_SECONDS = 75
STEP_SECONDS = 60
CACHE_SECONDS = 40
MFA_POLL_MS = 5_000

EXIT_OK, EXIT_LOGIN, EXIT_MFA_TIMEOUT, EXIT_NETWORK, EXIT_OTHER = 0, 2, 3, 4, 5
EXIT_MFA_PERSON, EXIT_BLOCKED = 6, 7

CHALLENGE_TEXT = re.compile(
    r"captcha|i'?m not a robot|verify (that )?you are (a )?human|are you a robot|"
    r"unusual (traffic|activity)|pardon our interruption|press (and|&) hold|"
    r"access denied|request (was )?blocked|security check|bot detection",
    re.I,
)
CHALLENGE_FRAME = re.compile(
    r"captcha|arkoselabs|funcaptcha|challenges\.cloudflare|perimeterx", re.I
)
LOGGED_IN_TEXT = re.compile(r"welcome,|claims & spending|log ?out|sign ?out", re.I)
LOGIN_ERROR_TEXT = re.compile(
    r"incorrect|invalid|not match|locked|try again|disabled|expired", re.I
)
CODE_INPUTS = [
    "#verificationCode",
    'input[autocomplete="one-time-code"]',
    'input[name*="code" i]',
    'input[id*="code" i]',
    'input[inputmode="numeric"]',
]
CACHE_PAGES = [
    ("/claims", ("claims",)),
    ("/claims/EOBs", ("eobSummary",)),
    ("/coverage/authorizations", ("preService",)),
]
FETCH_JS = """async (url) => {
  let t = sessionStorage.getItem('ngx-webstorage|wellmarkjwt');
  try { t = JSON.parse(t); } catch (e) {}
  const headers = t ? {Authorization: t, 'vnd.wellmark.clientappname': 'member-portal'} : {};
  const r = await fetch(url, {credentials: 'include', headers});
  const b = new Uint8Array(await r.arrayBuffer());
  let s = '';
  for (let i = 0; i < b.length; i += 32768) s += String.fromCharCode.apply(null, b.subarray(i, i + 32768));
  return {status: r.status, b64: btoa(s)};
}"""


class Stop(Exception):
    """Ends the run with an exit code, a status and optional page dump."""

    def __init__(self, code: int, state: str, detail: str, dump: str = "", **extra):
        super().__init__(detail)
        self.code, self.state, self.detail, self.dump, self.extra = code, state, detail, dump, extra


def write_status(out: Path, state: str, detail: str = "", **extra) -> None:
    payload = {"state": state, "detail": detail, "ts": time.time(), **extra}
    (out / "status.json").write_text(json.dumps(payload))
    print(f"[status] {state} {detail}".rstrip(), flush=True)


def scrub(message: str) -> str:
    """Drop query strings (signed links) from error text."""
    return re.sub(r"(https?://[^\s?\"']+)\?[^\s\"']*", r"\1?...", message)


def launch(p, headed: bool):
    options = {"headless": not headed}
    # Chromium does not pick up HTTPS_PROXY by itself; the cloud egress needs it.
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        options["proxy"] = {"server": proxy, "bypass": "localhost,127.0.0.1"}
    try:
        return p.chromium.launch(**options)
    except Exception:
        executable = find_chromium_executable()
        if not executable:
            raise
        return p.chromium.launch(executable_path=executable, **options)


def body_text(page, limit: int = 20_000) -> str:
    try:
        return page.locator("body").inner_text(timeout=5_000)[:limit]
    except Exception:
        return ""


def visible(page, selectors: list[str]):
    for selector in selectors:
        try:
            locator = page.locator(selector)
            for i in range(min(locator.count(), 5)):
                if locator.nth(i).is_visible():
                    return locator.nth(i)
        except Exception:
            continue
    return None


def dump(page, out: Path, name: str) -> None:
    """Page text and screenshot as evidence (credential fields emptied first)."""
    try:
        for selector in ("#username", "#password"):
            if page.locator(selector).count():
                page.locator(selector).first.fill("")
        (out / f"{name}.txt").write_text(f"URL: {scrub(page.url)}\n\n{body_text(page)}")
        page.screenshot(path=str(out / f"{name}.png"), full_page=True)
    except Exception:
        pass


def challenge_reason(page) -> str | None:
    match = CHALLENGE_TEXT.search(body_text(page, 3_000)) or CHALLENGE_TEXT.search(page.url)
    if match:
        return f"challenge page ({match.group(0)!r}) at {urlparse(page.url).netloc}"
    for frame in page.frames[1:]:
        url = frame.url or ""
        if not CHALLENGE_FRAME.search(url) or "size=invisible" in url:
            continue
        try:
            element = frame.frame_element()
            box = element.bounding_box()
            if element.is_visible() and box and box["width"] > 30 and box["height"] > 30:
                return f"CAPTCHA frame from {urlparse(url).netloc}"
        except Exception:
            continue
    return None


def page_state(page) -> str | None:
    """'challenge', 'mfa', 'login', 'home' or None (loading / unknown)."""
    if challenge_reason(page):
        return "challenge"
    if "/mfa" in page.url.lower() or visible(page, CODE_INPUTS[:2]):
        return "mfa"
    if visible(page, ["#username"]) and visible(page, ["#password"]):
        return "login"
    if page.url.startswith(PORTAL) and LOGGED_IN_TEXT.search(body_text(page, 5_000)):
        return "home"
    return None


def wait_for_state(page, wanted: set[str], seconds: int) -> str | None:
    deadline = time.time() + seconds
    state = None
    while time.time() < deadline:
        state = page_state(page)
        if state in wanted or state == "challenge":
            return state
        page.wait_for_timeout(1_000)
    return state


def stop_if_challenge(page, state: str | None) -> None:
    if state == "challenge":
        raise Stop(EXIT_BLOCKED, "blocked", challenge_reason(page) or "challenge page", "blocked")


def stop_if_stuck(page, mime_errors: list, waited: int) -> None:
    """The portal app never starts ("Loading") when Wellmark refuses the browser."""
    shown = " ".join(body_text(page, 200).split())[:60]
    if page.url.startswith(PORTAL) and shown.lower() in ("", "loading"):
        raise Stop(
            EXIT_BLOCKED,
            "blocked",
            f"portal did not load in {waited}s (page shows {shown!r}; {len(mime_errors)} "
            "scripts/styles answered with HTML). Wellmark refuses this headless browser: "
            "bot check, stopped without workaround",
            "blocked",
        )


def open_portal(page, out: Path, mime_errors: list) -> str:
    write_status(out, "loading_portal")
    page.goto(PORTAL + "/", timeout=NAV_MS, wait_until="domcontentloaded")
    state = wait_for_state(page, {"login", "mfa", "home"}, PORTAL_LOAD_SECONDS)
    stop_if_challenge(page, state)
    if state is None:
        stop_if_stuck(page, mime_errors, PORTAL_LOAD_SECONDS)
        raise Stop(EXIT_OTHER, "error", "login page not recognized", "portal_unrecognized")
    return state


def submit_credentials(page, out: Path, user: str, password: str) -> str:
    write_status(out, "logging_in")
    page.locator("#username").first.fill(user)
    page.locator("#password").first.fill(password)
    page.locator("#password").first.press("Enter")
    state = wait_for_state(page, {"mfa", "home"}, STEP_SECONDS)
    stop_if_challenge(page, state)
    if state not in ("mfa", "home"):
        match = LOGIN_ERROR_TEXT.search(body_text(page, 3_000))
        hint = f" (page says {match.group(0)!r})" if match else ""
        raise Stop(EXIT_LOGIN, "error", f"login failed{hint}", "login_failed")
    return state


def mfa_channel(text: str) -> str:
    """'email', 'sms' or 'unknown' from the verify page text."""
    match = re.search(r"sent to\s*\(?([^)\n]{3,80})\)?", text, re.I)
    target = match.group(1) if match else ""
    if "@" in target:
        return "email"
    if re.search(r"[\d•*]", target) or re.search(r"text message|\bsms\b", text, re.I):
        return "sms"
    return "unknown"


def choose_email_method(page) -> bool:
    """On a method picker, pick e-mail if offered."""
    option = visible(
        page,
        [
            'label:has-text("mail")',
            '[role=radio]:has-text("mail")',
            'input[type=radio][value*="mail" i]',
            'button:has-text("mail")',
        ],
    )
    if not option:
        return False
    option.click()
    send = visible(
        page,
        [
            'button:has-text("Send")',
            'button:has-text("Continue")',
            'button:has-text("Next")',
            'button[type="submit"]',
        ],
    )
    if send:
        send.click()
    page.wait_for_timeout(3_000)
    return True


def submit_code(page, out: Path, code: str, channel: str, mime_errors: list) -> None:
    box = visible(page, CODE_INPUTS)
    if not box:
        raise Stop(EXIT_LOGIN, "error", "MFA code field not found", "mfa_failed")
    box.fill(code)
    box.press("Enter")
    write_status(out, "mfa_submitted", mfa_channel=channel)
    state = wait_for_state(page, {"home"}, STEP_SECONDS)
    stop_if_challenge(page, state)
    if state is None:
        stop_if_stuck(page, mime_errors, STEP_SECONDS)
    if state != "home":
        match = LOGIN_ERROR_TEXT.search(body_text(page, 3_000))
        hint = f" (page says {match.group(0)!r})" if match else ""
        raise Stop(EXIT_LOGIN, "error", f"not signed in after the MFA code{hint}", "mfa_failed")


def handle_mfa(page, out: Path, args, mime_errors: list) -> None:
    if not visible(page, CODE_INPUTS) and choose_email_method(page):
        for _ in range(20):
            if visible(page, CODE_INPUTS):
                break
            page.wait_for_timeout(1_000)
    text = body_text(page, 4_000)
    channel = mfa_channel(text)
    if channel != "email" and not (args.allow_sms or args.headed):
        raise Stop(
            EXIT_MFA_PERSON,
            "error",
            f"MFA code goes by {channel}, so it needs the person "
            "(rerun with --allow-sms or --headed when someone can pass the code)",
            mfa_channel=channel,
        )
    hint = " or type it in the window" if args.headed else ""
    write_status(out, "waiting_mfa", f"write the code to mfa_code.txt{hint}", mfa_channel=channel)
    code_file = out / "mfa_code.txt"
    deadline = time.time() + args.mfa_timeout
    while time.time() < deadline:
        if args.headed and page_state(page) == "home":
            return
        if code_file.exists():
            code = re.sub(r"\D", "", code_file.read_text())
            if len(code) >= 4:
                code_file.unlink(missing_ok=True)
                submit_code(page, out, code, channel, mime_errors)
                return
        page.wait_for_timeout(MFA_POLL_MS)
    raise Stop(EXIT_MFA_TIMEOUT, "error", "MFA timeout", mfa_channel=channel)


def read_cache(page) -> dict:
    try:
        raw = page.evaluate("() => sessionStorage.getItem('cachedMemberInfo')")
        data = json.loads(raw) if raw else {}
    except Exception:
        return {}
    if isinstance(data, list):
        data = data[0] if data else {}
    return data if isinstance(data, dict) else {}


def load_member_info(page, out: Path) -> tuple[dict, list[str]]:
    write_status(out, "reading", "claims, EOBs, authorizations")
    info: dict = {}
    for path, keys in CACHE_PAGES:
        if all(k in info for k in keys):
            continue
        page.goto(PORTAL + path, timeout=NAV_MS, wait_until="domcontentloaded")
        deadline = time.time() + CACHE_SECONDS
        while time.time() < deadline:
            info = read_cache(page) or info
            if all(k in info for k in keys):
                break
            stop_if_challenge(page, page_state(page))
            page.wait_for_timeout(1_500)
    missing = [k for k in ("claims", "eobSummary", "preService") if k not in info]
    return info, missing


def iso_date(value) -> str:
    """'2026-10-16T05:00:00.000Z' or '10/29/2026' -> '2026-10-16' ('' if unknown)."""
    text = str(value or "").strip()
    match = re.match(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if match:
        return f"{match.group(3)}-{int(match.group(1)):02d}-{int(match.group(2)):02d}"
    return ""


def slug(text, limit: int = 40) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", str(text or "")).strip("-")[:limit] or "x"


def plan_documents(info: dict, since: str) -> tuple[list[dict], list[dict]]:
    """EOB and authorization-letter downloads; 'selected' = inside --since."""
    eobs = []
    for eob in info.get("eobSummary") or []:
        key = eob.get("documentKey") or ""
        if not key:
            continue
        issued = iso_date(eob.get("issuedDate"))
        icns = [i.get("icn") for i in eob.get("icnInfo") or [] if i.get("icn")]
        api = f"{API}/member-portal-api/v1/document/eob/documentid/{quote(key)}?sendPage=false"
        if icns:
            api += f"&icn={quote(icns[0])}"
        eobs.append({
            "date": issued,
            "icns": icns,
            "providers": sorted({i.get("providerName") or "" for i in eob.get("icnInfo") or []} - {""}),
            "selected": not since or issued >= since,
            "file": f"eobs/EOB_{issued}_{slug(key, 8)}.pdf",
            "api": api,
        })
    letters = []
    for auth in info.get("preService") or []:
        for letter in auth.get("authLetter") or []:
            key = letter.get("authLetterKey") or ""
            if not key:
                continue
            created = iso_date(letter.get("createdDt"))
            name = letter.get("letterName") or "Letter"
            letters.append({
                "date": created,
                "auth": auth,
                "name": name,
                "selected": not since or created >= since,
                "file": (
                    f"auth_letters/AUTH_{created}_{slug(auth.get('authId'), 20)}_"
                    f"{slug(name.split()[0], 20)}_{slug(key, 8)}.pdf"
                ),
                "api": f"{API}/member-portal-api/v1/document/authorization/documentid/{quote(key)}?sendPage=false",
            })
    return eobs, letters


def fetch_document(page, api_url: str, dest: Path) -> None:
    reply = page.evaluate(FETCH_JS, api_url)
    if reply.get("status") != 200:
        raise RuntimeError(f"document API HTTP {reply.get('status')}")
    body = base64.b64decode(reply.get("b64") or "")
    if not body.startswith(b"%PDF"):
        text = body.decode("utf-8", "replace").strip()
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = text
        if isinstance(parsed, dict):
            parsed = next((v for v in parsed.values() if isinstance(v, str) and v.startswith("http")), "")
        link = str(parsed).strip().strip('"')
        if not link.startswith("http"):
            raise RuntimeError("document API did not return a PDF or a link")
        response = page.context.request.get(link, headers={"Referer": PORTAL + "/"}, timeout=120_000)
        if not response.ok:
            raise RuntimeError(f"document link HTTP {response.status}")
        body = response.body()
    if not body.startswith(b"%PDF"):
        raise RuntimeError("download is not a PDF")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)


def download_all(page, out: Path, docs: list[dict]) -> None:
    todo = [d for d in docs if d["selected"]]
    for n, doc in enumerate(todo, 1):
        dest = out / doc["file"]
        if dest.exists() and dest.read_bytes()[:4] == b"%PDF":
            doc["downloaded"] = True  # kept from an earlier run into the same --out
            continue
        write_status(out, "downloading", f"{n}/{len(todo)}")
        for attempt in (1, 2):
            try:
                fetch_document(page, doc["api"], dest)
                doc["downloaded"] = True
                doc.pop("error", None)
                break
            except Exception as e:
                doc["error"] = scrub(str(e))[:200]
                page.wait_for_timeout(2_000 * attempt)


def pdf_text(path: Path) -> str | None:
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    try:
        run = subprocess.run([exe, "-layout", str(path), "-"], capture_output=True, text=True, timeout=60)
    except Exception:
        return None
    return run.stdout if run.returncode == 0 else None


def add_letter_text(out: Path, letters: list[dict]) -> None:
    """Text next to each letter; letters repeated with the same text are marked."""
    first_by_text: dict[str, str] = {}
    for doc in letters:
        if not doc.get("downloaded"):
            continue
        pdf = out / doc["file"]
        text = pdf_text(pdf)
        if text is None:
            continue
        pdf.with_suffix(".txt").write_text(text)
        doc["text_file"] = str(Path(doc["file"]).with_suffix(".txt"))
        digest = hashlib.sha256(" ".join(text.split()).encode()).hexdigest()
        if digest in first_by_text:
            doc["same_text_as"] = first_by_text[digest]
        else:
            first_by_text[digest] = doc["file"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def auth_outcome(auth: dict) -> str:
    outcomes = sorted({line.get("outcome") or "" for line in auth.get("authSrvcLine") or []} - {""})
    return ", ".join(outcomes)


def build_index(out: Path, info: dict, eobs: list[dict], letters: list[dict], since: str) -> list[dict]:
    claims = info.get("claims") or []
    status_by_icn = {c.get("icn"): c.get("claimStatus") or "" for c in claims}
    eob_file_by_icn = {}
    for eob in eobs:
        for icn in eob["icns"]:
            if eob.get("downloaded"):
                eob_file_by_icn.setdefault(icn, eob["file"])
    recent_icns = {icn for eob in eobs if eob["selected"] for icn in eob["icns"]}

    def file_fields(doc: dict) -> dict:
        if not doc.get("downloaded"):
            return {"file": None, "error": doc.get("error", "not downloaded")}
        fields = {"file": doc["file"], "sha256": sha256(out / doc["file"])}
        for key in ("text_file", "same_text_as"):
            if doc.get(key):
                fields[key] = doc[key]
        return fields

    items = []
    for eob in eobs:
        if not eob["selected"]:
            continue
        statuses = sorted({status_by_icn.get(i) for i in eob["icns"]} - {None, ""})
        providers = ", ".join(eob["providers"][:2]) + (f" +{len(eob['providers']) - 2}" if len(eob["providers"]) > 2 else "")
        items.append({
            "date": eob["date"],
            "type": "eob",
            "title": f"EOB {eob['date']} - {len(eob['icns'])} claim(s): {providers}",
            "status": ", ".join(statuses),
            "reference": eob["icns"],
            **file_fields(eob),
        })

    letters_by_auth: dict[str, list[dict]] = {}
    for letter in letters:
        letters_by_auth.setdefault(letter["auth"].get("authId"), []).append(letter)
        if not letter["selected"]:
            continue
        auth = letter["auth"]
        lines = auth.get("authSrvcLine") or [{}]
        items.append({
            "date": letter["date"],
            "type": "authorization_letter",
            "title": f"{letter['name']} - {lines[0].get('serviceType', '')} (ref {auth.get('authId')})",
            "status": auth_outcome(auth),
            "reference": auth.get("authId"),
            **file_fields(letter),
        })

    for auth in info.get("preService") or []:
        lines = auth.get("authSrvcLine") or [{}]
        received = iso_date(auth.get("receivedDt"))
        decided = max((iso_date(line.get("srvReviewedDt")) for line in lines), default="")
        own_letters = letters_by_auth.get(auth.get("authId"), [])
        if since and received < since and decided < since and not any(l["selected"] for l in own_letters):
            continue
        types = ", ".join(sorted({line.get("type") or "" for line in lines} - {""}))
        items.append({
            "date": received,
            "type": "authorization",
            "title": f"{lines[0].get('serviceType', '')} - {lines[0].get('request', '')} ({types})",
            "status": auth_outcome(auth),
            "authorization_status": auth.get("authStatus"),
            "reference": auth.get("authId"),
            "decided": decided,
            "service_dates": f"{iso_date(lines[0].get('srvLineStartDt'))} to {iso_date(lines[0].get('srvLineEndDt'))}",
            "units": lines[0].get("units"),
            "requested_by": auth.get("submittedBy"),
            "file": next((l["file"] for l in sorted(own_letters, key=lambda l: l["date"], reverse=True) if l.get("downloaded")), None),
        })

    for claim in claims:
        first = iso_date(claim.get("firstDateOfService"))
        if since and first < since and claim.get("icn") not in recent_icns:
            continue
        amounts = claim.get("amounts") or {}
        items.append({
            "date": first,
            "type": "claim",
            "title": f"{(claim.get('provider') or {}).get('name', '')} - "
                     f"{claim.get('aggregatedClaimCategories') or claim.get('claimCategory') or ''}",
            "status": claim.get("claimStatus"),
            "reference": claim.get("icn"),
            "service_end": iso_date(claim.get("lastDateOfService")),
            "category": claim.get("claimCategory"),
            "billed": amounts.get("totalBilled"),
            "plan_paid": amounts.get("paidAmount"),
            "member_owes": amounts.get("totalMemberLiability"),
            "denial_message": "; ".join(claim.get("claimDenialMessage") or []),
            "file": eob_file_by_icn.get(claim.get("icn")),
        })

    order = {"authorization_letter": 0, "authorization": 1, "eob": 2, "claim": 3}
    items.sort(key=lambda i: (i["date"] or "", -order[i["type"]]), reverse=True)
    return items


def write_outputs(out: Path, info: dict, eobs: list[dict], letters: list[dict], since: str, missing: list[str]) -> dict:
    (out / "portal_cache.json").write_text(json.dumps(info, indent=1))
    items = build_index(out, info, eobs, letters, since)
    claims = info.get("claims") or []
    summary = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "since": since or None,
        "portal_search_date": info.get("searchDate"),
        "ytd_out_of_pocket": round(float(info.get("ytdOOPCosts") or 0), 2),
        "claims_total": len(claims),
        "claims_by_status": dict(Counter(c.get("claimStatus") for c in claims)),
        "eobs_total": len(eobs),
        "eobs_downloaded": sum(1 for d in eobs if d.get("downloaded")),
        "authorizations_total": len(info.get("preService") or []),
        "letters_total": len(letters),
        "letters_downloaded": sum(1 for d in letters if d.get("downloaded")),
        "letters_same_text": sum(1 for d in letters if d.get("same_text_as")),
        "download_errors": sum(1 for d in eobs + letters if d["selected"] and not d.get("downloaded")),
        "missing_from_cache": missing,
    }
    (out / "index.json").write_text(json.dumps({"summary": summary, "items": items}, indent=1))
    return summary


def parse_since(value: str) -> str:
    """YYYY-MM-DD or an RFC 3339 timestamp (last_sync) -> YYYY-MM-DD."""
    day = (value or "")[:10]
    try:
        date.fromisoformat(day)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {value!r}")
    return day


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Wellmark EOBs, letters and claims.")
    parser.add_argument("--out", required=True, help="output directory (scratchpad; never the repo)")
    parser.add_argument("--since", type=parse_since, help="only documents dated on/after YYYY-MM-DD")
    parser.add_argument("--allow-sms", action="store_true", help="wait for an SMS code in mfa_code.txt")
    parser.add_argument("--headed", action="store_true", help="visible browser; a person may type the code")
    parser.add_argument("--mfa-timeout", type=int, default=300, help="seconds to wait for the MFA code")
    args = parser.parse_args()

    since = args.since or ""
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_status(out, "starting", f"since {since}" if since else "all documents")
    user = os.environ.get("WELLMARK_USER", "")
    password = os.environ.get("WELLMARK_PASS", "")
    if not user or not password:
        write_status(out, "error", "missing env vars WELLMARK_USER/WELLMARK_PASS")
        return EXIT_LOGIN

    with sync_playwright() as p:
        try:
            browser = launch(p, args.headed)
        except Exception as e:
            first_line = (scrub(str(e)).splitlines() or [""])[0][:150]
            hint = " (--headed needs a screen)" if args.headed else ""
            write_status(out, "error", f"browser launch failed: {first_line}{hint}")
            return EXIT_OTHER
        page = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()
        page.set_default_timeout(NAV_MS)
        mime_errors: list[str] = []
        page.on(
            "console",
            lambda m: mime_errors.append(m.text) if m.type == "error" and "MIME type" in m.text else None,
        )
        try:
            state = open_portal(page, out, mime_errors)
            if state == "login":
                state = submit_credentials(page, out, user, password)
            if state == "mfa":
                handle_mfa(page, out, args, mime_errors)
            info, missing = load_member_info(page, out)
            if "claims" not in info and "preService" not in info:
                raise Stop(EXIT_OTHER, "error", "portal cache not found after login", "cache_missing")
            eobs, letters = plan_documents(info, since)
            download_all(page, out, eobs + letters)
            add_letter_text(out, letters)
            summary = write_outputs(out, info, eobs, letters, since, missing)
            write_status(
                out,
                "done",
                f"{summary['eobs_downloaded']} EOBs, {summary['letters_downloaded']} letters, "
                f"{summary['claims_total']} claims; {summary['download_errors']} download errors",
            )
            return EXIT_OK
        except Stop as stop:
            if stop.dump:
                dump(page, out, stop.dump)
            write_status(out, stop.state, stop.detail, **stop.extra)
            return stop.code
        except Exception as e:
            message = scrub(str(e))
            dump(page, out, "error_page")
            if "ERR_TUNNEL_CONNECTION_FAILED" in message or "ERR_PROXY" in message:
                write_status(out, "error", "network blocked by environment policy")
                return EXIT_NETWORK
            write_status(out, "error", message[:300])
            return EXIT_OTHER
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
