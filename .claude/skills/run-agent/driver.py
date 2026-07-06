#!/usr/bin/env python3
"""End-to-end smoke driver for the medical-appointment agent.

Boots a local mock MyChart (mock_mychart.py), runs the REAL scraper
(agent/mychart.py) against it under Chromium/Playwright, feeds the MFA code
when the scraper asks for it, and asserts the expected artifacts were
produced (login -> MFA -> upcoming visits -> past visits dumps + screenshots).

This drives every layer of mychart.py except the live portal: the login
selectors, the email-code MFA handshake protocol, persona/no-persona, and the
Visits scraping + page dumps. No credentials, no network egress.

Usage:
    python .claude/skills/run-agent/driver.py [--port 8799] [--keep]

Exit 0 on success; non-zero with a diagnostic on failure.
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
REPO_ROOT = SKILL_DIR.parents[2]
AGENT_DIR = REPO_ROOT / "agent"
MOCK = SKILL_DIR / "mock_mychart.py"
SCRAPER = AGENT_DIR / "mychart.py"


def free_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def wait_for_port(port: int, timeout: float = 15) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.2)
    return False


def read_status(out_dir: Path) -> dict:
    try:
        return json.loads((out_dir / "status.json").read_text())
    except Exception:
        return {}


def fail(msg: str, mock, scraper=None) -> int:
    print(f"\n[FAIL] {msg}", file=sys.stderr)
    if scraper and scraper.poll() is None:
        scraper.terminate()
    if mock and mock.poll() is None:
        mock.terminate()
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8799)
    parser.add_argument("--keep", action="store_true", help="keep artifacts dir")
    args = parser.parse_args()

    port = free_port(args.port)
    out_dir = SKILL_DIR / "_smoke_out"
    out_dir.mkdir(exist_ok=True)
    for stale in out_dir.glob("*"):
        stale.unlink()

    print(f"[1/5] starting mock MyChart on :{port}")
    mock = subprocess.Popen([sys.executable, str(MOCK), "--port", str(port)])
    if not wait_for_port(port):
        return fail("mock server never came up", mock)

    env = {
        **os.environ,
        "MYCHART_BASE_URL": f"http://127.0.0.1:{port}/mychart",
        "MYCHART_EU_USER": "smoke-user",
        "MYCHART_EU_PASS": "smoke-pass",
    }
    print("[2/5] launching real scraper (agent/mychart.py) against mock")
    scraper = subprocess.Popen(
        [sys.executable, str(SCRAPER), "--account", "eu", "--out", str(out_dir)],
        env=env,
    )

    print("[3/5] waiting for MFA prompt, then feeding code 246810")
    fed = False
    deadline = time.time() + 120
    while time.time() < deadline:
        if scraper.poll() is not None:
            break
        state = read_status(out_dir).get("state")
        if state == "waiting_mfa" and not fed:
            (out_dir / "mfa_code.txt").write_text("246810")
            fed = True
            print("      -> MFA code written")
        if state in ("done", "error"):
            break
        time.sleep(0.5)

    rc = scraper.wait(timeout=30)
    mock.terminate()

    print(f"[4/5] scraper exited rc={rc}; verifying artifacts")
    if not fed:
        return fail("scraper never reached the MFA challenge", mock)
    if rc != 0:
        return fail(f"scraper rc={rc}, status={read_status(out_dir)}", mock)

    required = [
        "status.json", "result.json",
        "mfa_challenge.txt", "home.txt",
        "visits_upcoming.txt", "visits_upcoming.png",
        "visits_past.txt", "visits_past.png",
    ]
    missing = [f for f in required if not (out_dir / f).exists()]
    if missing:
        return fail(f"missing artifacts: {missing}", mock)

    upcoming = (out_dir / "visits_upcoming.txt").read_text()
    past = (out_dir / "visits_past.txt").read_text()
    if "Cardiology" not in upcoming:
        return fail("upcoming dump missing expected 'Cardiology'", mock)
    if "Ophthalmology" not in past:
        return fail("past dump missing expected 'Ophthalmology'", mock)

    print("[5/5] OK — login, MFA handshake, and Visits scraping all worked")
    print(f"      artifacts in: {out_dir}")
    print(f"      upcoming visits dump ({len(upcoming)} chars), "
          f"past visits dump ({len(past)} chars)")
    if not args.keep:
        print("      (pass --keep to retain artifacts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
