#!/usr/bin/env python3
"""Interactive MyChart explorer: one long-lived Chromium page driven over a
localhost HTTP API, for walking the live portal step by step (discovering
pages, downloading records) when a scripted scraper is not enough.

Secrets never travel through the command channel: /fill_secret reads the
value from a MYCHART_* environment variable inside this process.

Run (background):  python3 agent/mychart_explorer.py --out DIR [--port 8765]
Drive with curl, e.g.:
    curl -s 'localhost:8765/goto?u=/mychart/Authentication/Login'
    curl -s 'localhost:8765/fill_secret?sel=%23Login&var=MYCHART_MAE_USER'
    curl -s 'localhost:8765/click?sel=%23submit'          # Continue -> password step
    curl -s 'localhost:8765/fill_secret?sel=%23Password&var=MYCHART_MAE_PASS'
    curl -s 'localhost:8765/click?sel=%23submit'
    curl -s 'localhost:8765/click?sel=%23emailCode'       # MFA code by email
    curl -s 'localhost:8765/fill?sel=%23twofactorcode&val=123456'
    curl -s 'localhost:8765/click?sel=%23submitSecondaryValidation'

Commands (GET, JSON reply): goto?u=  url  text?sel=&max=  save?name=  shot?name=&full=1
links?f=  buttons  inputs  click?sel=|text=[&exact=1]  fill?sel=&val=
fill_secret?sel=&var=  press?sel=&key=  download?sel=|text=[&name=][&timeout=]
note_text  eval?js=  back  wait?ms=  quit

Portal notes (UIHC, 2026-10):
- Requested Records downloads ask "Confirm download" in a dialog; click
  `[role=dialog] button._LaboredCommand` inside /download. Several files share
  the suggested name "Requested Record.pdf" — pass name= to keep them apart.
- "View, Download, or Send Visit Records" exports at most 50 visits per
  request; use date ranges (/MyChart/app/record-download/document-preview?
  selectionType=dateRange&startDate=YYYY-MM-DD&endDate=YYYY-MM-DD), then
  "Download all (N)" -> "Request download"; files appear in Requested Records.
- Clinical note text lives in the shadow DOM of .InternalReportViewerWrapper;
  body innerText does not include it — use /note_text.
"""

import argparse
import json
import os
import queue
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from mychart import find_chromium_executable  # noqa: E402

BASE = os.environ.get("MYCHART_HOST", "https://mychart.uihealthcare.org")
NAV_MS = 45_000
NOTE_JS = """(() => {
  const host = document.querySelector('.InternalReportViewerWrapper');
  if (!host || !host.shadowRoot) return null;
  return Array.from(host.shadowRoot.children).map(c => c.innerText || c.textContent || '').join('\\n');
})()"""

jobs: "queue.Queue[tuple[str, dict, dict, threading.Event]]" = queue.Queue()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        args = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        box: dict = {}
        done = threading.Event()
        jobs.put((parsed.path.strip("/"), args, box, done))
        done.wait(timeout=600)
        body = json.dumps(box.get("result", {"error": "timeout"}), ensure_ascii=False, indent=1).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def settle(page):
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        pass
    page.wait_for_timeout(800)


def visible_text(page, sel=None, limit=6000):
    loc = page.locator(sel).first if sel else page.locator("body")
    txt = re.sub(r"\n{3,}", "\n\n", loc.inner_text(timeout=10_000))
    return txt[:limit], len(txt)


def unique_path(folder: Path, name: str) -> Path:
    target = folder / name
    stem, suffix, n = target.stem, target.suffix, 2
    while target.exists():
        target = folder / f"{stem} ({n}){suffix}"
        n += 1
    return target


def launch(p):
    options = {"headless": True}
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


def locate(page, a):
    if "sel" in a:
        return page.locator(a["sel"]).first
    if a.get("role"):
        return page.get_by_role(a["role"], name=a["text"], exact=a.get("exact") == "1").first
    return page.get_by_text(a["text"], exact=a.get("exact") == "1").first


def run(out: Path, port: int):
    out.mkdir(parents=True, exist_ok=True)
    downloads = out / "downloads"
    downloads.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    with sync_playwright() as p:
        browser = launch(p)
        ctx = browser.new_context(accept_downloads=True, viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        page.set_default_timeout(NAV_MS)
        print(f"explorer ready on :{port}", flush=True)
        shot_n = 0

        while True:
            cmd, a, box, done = jobs.get()
            try:
                if cmd == "goto":
                    page.goto(urljoin(BASE, a["u"]), timeout=NAV_MS, wait_until="domcontentloaded")
                    settle(page)
                    res = {"url": page.url, "title": page.title()}
                elif cmd == "url":
                    res = {"url": page.url, "title": page.title()}
                elif cmd == "text":
                    txt, n = visible_text(page, a.get("sel"), int(a.get("max", 6000)))
                    res = {"url": page.url, "chars": n, "text": txt}
                elif cmd == "save":
                    name = a.get("name", "page")
                    txt, _ = visible_text(page, a.get("sel"), 10_000_000)
                    (out / f"{name}.txt").write_text(txt)
                    (out / f"{name}.html").write_text(page.content())
                    res = {"saved": str(out / f"{name}.txt"), "chars": len(txt)}
                elif cmd == "shot":
                    shot_n += 1
                    path = out / f"{a.get('name', 'shot')}_{shot_n:02d}.png"
                    page.screenshot(path=str(path), full_page=a.get("full", "0") == "1")
                    res = {"shot": str(path)}
                elif cmd == "links":
                    flt = a.get("f", "").lower()
                    items = page.eval_on_selector_all(
                        "a[href]",
                        "els => els.filter(e => e.offsetParent !== null)"
                        ".map(e => [e.innerText.trim().slice(0,80), e.getAttribute('href')])",
                    )
                    res = {"links": [i for i in items if flt in (i[0] + i[1]).lower()][: int(a.get("max", 120))]}
                elif cmd == "buttons":
                    res = {"buttons": page.eval_on_selector_all(
                        "button, [role=button], input[type=submit], [role=tab]",
                        "els => els.filter(e => e.offsetParent !== null).map(e => [e.tagName, e.id,"
                        " (e.innerText || e.value || e.getAttribute('aria-label') || '').trim().slice(0,80)])",
                    )[:150]}
                elif cmd == "inputs":
                    res = {"inputs": page.eval_on_selector_all(
                        "input, select, textarea",
                        "els => els.filter(e => e.offsetParent !== null)"
                        ".map(e => [e.tagName, e.type, e.id, e.name, e.getAttribute('aria-label')])",
                    )}
                elif cmd == "click":
                    locate(page, a).click(timeout=20_000)
                    settle(page)
                    res = {"url": page.url, "title": page.title()}
                elif cmd == "fill":
                    page.locator(a["sel"]).first.fill(a["val"])
                    res = {"ok": True}
                elif cmd == "fill_secret":
                    var = a["var"]
                    if not var.startswith("MYCHART_"):
                        raise ValueError("only MYCHART_* variables")
                    page.locator(a["sel"]).first.fill(os.environ[var])
                    res = {"ok": True, "filled_from": var}
                elif cmd == "press":
                    page.locator(a["sel"]).first.press(a.get("key", "Enter"))
                    settle(page)
                    res = {"url": page.url}
                elif cmd == "download":
                    with page.expect_download(timeout=int(a.get("timeout", 90)) * 1000) as dl:
                        locate(page, a).click()
                    d = dl.value
                    target = unique_path(downloads, a.get("name") or d.suggested_filename)
                    d.save_as(str(target))
                    res = {"saved": str(target), "bytes": target.stat().st_size,
                           "suggested": d.suggested_filename}
                elif cmd == "note_text":
                    txt = None
                    for _ in range(8):
                        txt = page.evaluate(NOTE_JS)
                        if txt and len(txt) > 50:
                            break
                        page.wait_for_timeout(1000)
                    res = {"url": page.url, "chars": len(txt or ""), "text": txt}
                elif cmd == "eval":
                    res = {"value": page.evaluate(a["js"])}
                elif cmd == "back":
                    page.go_back()
                    settle(page)
                    res = {"url": page.url}
                elif cmd == "wait":
                    page.wait_for_timeout(int(a.get("ms", 2000)))
                    res = {"url": page.url}
                elif cmd == "quit":
                    box["result"] = {"bye": True}
                    done.set()
                    break
                else:
                    res = {"error": f"unknown command {cmd}"}
            except Exception as e:
                res = {"error": str(e)[:800], "url": page.url}
            box["result"] = res
            done.set()

        browser.close()
    server.shutdown()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="artifacts directory (keep it out of the repo)")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    run(Path(args.out), args.port)
