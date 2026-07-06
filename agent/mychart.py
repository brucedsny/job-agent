#!/usr/bin/env python3
"""MyChart (Epic) appointment scraper for UIHC.

Logs into a MyChart account with Playwright, navigates to the Visits pages
and dumps page text + screenshots to an output directory. Parsing of the
dumps into structured appointments is done by the orchestrating agent
(see .claude/skills/check-medico), which is far more robust to Epic UI
changes than hardcoded selectors.

Usage:
    python agent/mychart.py --account eu --out /path/to/outdir

Protocol with the orchestrator:
    - status.json in the out dir is updated as the run progresses:
        {"state": "starting" | "logging_in" | "waiting_mfa" | "scraping"
                 | "done" | "error", "detail": "..."}
    - When state is "waiting_mfa", the orchestrator must write the 6-digit
      verification code (sent by MyChart to the patient's email) into
      <out>/mfa_code.txt. The scraper polls that file for up to 5 minutes.
    - On success, artifacts are listed in result.json.

Exit codes: 0 ok, 2 login failed, 3 MFA timeout, 4 network blocked, 5 other.
"""

import argparse
import glob
import json
import os
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

CONFIG_PATH = Path(__file__).parent / "config.json"
MFA_POLL_SECONDS = 5
MFA_TIMEOUT_SECONDS = 300
NAV_TIMEOUT_MS = 45_000


def load_account(account_id: str) -> tuple[dict, dict]:
    config = json.loads(CONFIG_PATH.read_text())
    for account in config["accounts"]:
        if account["id"] == account_id:
            return config, account
    sys.exit(f"unknown account id: {account_id}")


def write_status(out_dir: Path, state: str, detail: str = "") -> None:
    (out_dir / "status.json").write_text(
        json.dumps({"state": state, "detail": detail, "ts": time.time()})
    )
    print(f"[status] {state} {detail}", flush=True)


def find_chromium_executable() -> str | None:
    """Fallback for version mismatch between playwright pip package and
    the pre-installed browsers in PLAYWRIGHT_BROWSERS_PATH."""
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
    for pattern in ("chromium-*/chrome-linux/chrome", "chromium/chrome-linux/chrome"):
        matches = sorted(glob.glob(str(Path(root) / pattern)))
        if matches:
            return matches[-1]
    return None


def launch_browser(p):
    try:
        return p.chromium.launch(headless=True)
    except Exception:
        executable = find_chromium_executable()
        if not executable:
            raise
        return p.chromium.launch(headless=True, executable_path=executable)


def first_visible(page, selectors: list[str]):
    for selector in selectors:
        locator = page.locator(selector)
        for i in range(min(locator.count(), 5)):
            element = locator.nth(i)
            if element.is_visible():
                return element
    return None


def dump_page(page, out_dir: Path, name: str) -> dict:
    text_path = out_dir / f"{name}.txt"
    png_path = out_dir / f"{name}.png"
    try:
        text_path.write_text(page.locator("body").inner_text(timeout=10_000))
    except Exception as e:
        text_path.write_text(f"<dump failed: {e}>")
    try:
        page.screenshot(path=str(png_path), full_page=True)
    except Exception:
        pass
    return {"text": str(text_path), "screenshot": str(png_path)}


def looks_logged_in(page) -> bool:
    try:
        body = page.locator("body").inner_text(timeout=10_000)
    except Exception:
        return False
    return bool(re.search(r"log\s*out|sign\s*out|visits|appointments", body, re.I)) and not re.search(
        r"forgot (username|password)", body, re.I
    )


def mfa_page_kind(page) -> str | None:
    """Return 'choose' (pick delivery method), 'code' (enter code) or None."""
    try:
        body = page.locator("body").inner_text(timeout=10_000).lower()
    except Exception:
        return None
    if not re.search(r"security code|verification code|verify your identity|two.step", body):
        return None
    if first_visible(page, ['input[name*="code" i]', 'input[id*="code" i]', 'input[inputmode="numeric"]']):
        return "code"
    return "choose"


def wait_for_mfa_code(out_dir: Path) -> str | None:
    code_file = out_dir / "mfa_code.txt"
    deadline = time.time() + MFA_TIMEOUT_SECONDS
    while time.time() < deadline:
        if code_file.exists():
            code = re.sub(r"\D", "", code_file.read_text())
            if len(code) >= 4:
                return code
        time.sleep(MFA_POLL_SECONDS)
    return None


def handle_mfa(page, out_dir: Path) -> bool:
    kind = mfa_page_kind(page)
    if kind is None:
        return True  # no MFA challenge

    if kind == "choose":
        email_button = first_visible(
            page, ['button:has-text("email")', 'a:has-text("email")', 'input[value*="email" i]']
        )
        if email_button:
            email_button.click()
            page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
        dump_page(page, out_dir, "mfa_choose")

    write_status(out_dir, "waiting_mfa", "write code to mfa_code.txt")
    dump_page(page, out_dir, "mfa_challenge")
    code = wait_for_mfa_code(out_dir)
    if not code:
        return False

    code_input = first_visible(
        page, ['input[name*="code" i]', 'input[id*="code" i]', 'input[inputmode="numeric"]', 'input[type="text"]']
    )
    if not code_input:
        return False
    code_input.fill(code)

    trust = first_visible(
        page, ['input[type="checkbox"][id*="trust" i]', 'input[type="checkbox"][name*="remember" i]']
    )
    if trust:
        try:
            trust.check()
        except Exception:
            pass

    submit = first_visible(
        page, ['button[type="submit"]', 'button:has-text("verify")', 'button:has-text("continue")', 'input[type="submit"]']
    )
    if submit:
        submit.click()
        page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
    return True


def login(page, login_url: str, username: str, password: str, out_dir: Path) -> bool:
    write_status(out_dir, "logging_in")
    page.goto(login_url, timeout=NAV_TIMEOUT_MS, wait_until="networkidle")

    user_input = first_visible(
        page, ["#Login", 'input[name="Login"]', 'input[name*="user" i]', 'input[type="text"]']
    )
    pass_input = first_visible(page, ['input[type="password"]'])
    if not user_input or not pass_input:
        dump_page(page, out_dir, "login_page_unrecognized")
        return False

    user_input.fill(username)
    pass_input.fill(password)
    submit = first_visible(
        page, ["#submit", 'button[type="submit"]', 'input[type="submit"]', 'button:has-text("sign in")']
    )
    if not submit:
        return False
    submit.click()
    page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)

    if not handle_mfa(page, out_dir):
        return False
    return looks_logged_in(page)


def switch_persona(page, persona: str, out_dir: Path) -> None:
    """Best-effort switch to a proxy persona (e.g. a parent's chart)."""
    try:
        page.get_by_text(persona, exact=False).first.click(timeout=10_000)
        page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
    except Exception as e:
        write_status(out_dir, "scraping", f"persona switch failed: {e}")
    dump_page(page, out_dir, "after_persona_switch")


def scrape_visits(page, base_url: str, out_dir: Path) -> list[dict]:
    artifacts = []
    write_status(out_dir, "scraping", "home")
    artifacts.append({"page": "home", **dump_page(page, out_dir, "home")})

    write_status(out_dir, "scraping", "visits")
    page.goto(f"{base_url}/Visits", timeout=NAV_TIMEOUT_MS, wait_until="networkidle")
    artifacts.append({"page": "visits_upcoming", **dump_page(page, out_dir, "visits_upcoming")})

    # Epic usually shows past visits behind a tab/link on the same page.
    past_tab = first_visible(
        page, ['button:has-text("past")', 'a:has-text("past")', '[role="tab"]:has-text("past")']
    )
    if past_tab:
        try:
            past_tab.click()
            page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
        except PWTimeout:
            pass
    artifacts.append({"page": "visits_past", **dump_page(page, out_dir, "visits_past")})
    return artifacts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", required=True, help="account id from config.json (eu|mae)")
    parser.add_argument("--out", required=True, help="output directory for artifacts")
    args = parser.parse_args()

    config, account = load_account(args.account)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_status(out_dir, "starting", args.account)

    username = os.environ.get(account["user_env"], "")
    password = os.environ.get(account["pass_env"], "")
    if not username or not password:
        write_status(out_dir, "error", f"missing env vars {account['user_env']}/{account['pass_env']}")
        return 2

    # MYCHART_BASE_URL overrides config — used by the run-agent driver to point
    # the scraper at a local mock MyChart instead of the live portal.
    base_url = os.environ.get("MYCHART_BASE_URL", config["mychart_base_url"]).rstrip("/")
    login_url = base_url + config.get("login_path", "/Authentication/Login")

    with sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page()
        page.set_default_timeout(NAV_TIMEOUT_MS)
        try:
            if not login(page, login_url, username, password, out_dir):
                status = json.loads((out_dir / "status.json").read_text())
                if status.get("state") == "waiting_mfa":
                    write_status(out_dir, "error", "MFA timeout")
                    return 3
                dump_page(page, out_dir, "login_failed")
                write_status(out_dir, "error", "login failed")
                return 2

            if account.get("persona"):
                switch_persona(page, account["persona"], out_dir)

            artifacts = scrape_visits(page, base_url, out_dir)
            (out_dir / "result.json").write_text(
                json.dumps(
                    {
                        "account": account["id"],
                        "label": account["label"],
                        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        "artifacts": artifacts,
                    },
                    indent=2,
                )
            )
            write_status(out_dir, "done")
            return 0
        except Exception as e:
            message = str(e)
            dump_page(page, out_dir, "error_page")
            if "ERR_TUNNEL_CONNECTION_FAILED" in message or "ERR_PROXY" in message:
                write_status(out_dir, "error", "network blocked by environment policy")
                return 4
            write_status(out_dir, "error", message[:500])
            return 5
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
