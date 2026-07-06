---
name: run-agent
description: Build, launch, and smoke-test the medical-appointment agent (MyChart UIHC scraper in agent/mychart.py). Use to run the scraper, drive it end-to-end offline, screenshot the visits pages, or verify a change to mychart.py without live credentials or network. Triggers on "run the agent", "test the scraper", "screenshot mychart", "does mychart.py still work".
---

# run-agent — drive the medical-appointment scraper

The runnable unit is `agent/mychart.py`: a Playwright/Chromium scraper that
logs into MyChart (UIHC), solves an email-code MFA challenge, and dumps the
Visits pages for the orchestrating `/check-medico` skill to parse. The live
portal needs real credentials and network egress that this environment blocks,
so the primary way to run it here is the **offline driver**, which boots a mock
MyChart and runs the real scraper against it.

Paths below are relative to the repo root (`/home/user/job-agent`).

## Prerequisites

Chromium is pre-installed (`PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`) — do
**not** run `playwright install`. Only the Python package is needed:

```bash
pip install -r agent/requirements.txt
```

No apt packages or `xvfb` are required: the scraper launches Chromium headless.

## Run (agent path) — offline end-to-end driver

This is the way to exercise the scraper. It starts `mock_mychart.py`, runs the
real `agent/mychart.py` against it, feeds the MFA code when the scraper asks,
and asserts the login → MFA → upcoming/past Visits dumps + screenshots were
produced. No credentials, no network.

```bash
python3 .claude/skills/run-agent/driver.py --keep
```

Expected tail on success (exit 0):

```
[4/5] scraper exited rc=0; verifying artifacts
[5/5] OK — login, MFA handshake, and Visits scraping all worked
```

Artifacts land in `.claude/skills/run-agent/_smoke_out/` (gitignored). With
`--keep`, inspect `visits_upcoming.png` / `visits_past.png` (rendered pages)
and `*.txt` (the text dumps the orchestrator parses). Omit `--keep` for a
pass/fail check.

Syntax-check everything first if you edited the scraper or mock:

```bash
python3 -m py_compile agent/mychart.py .claude/skills/run-agent/mock_mychart.py .claude/skills/run-agent/driver.py
```

## Run the scraper directly (against the mock)

To iterate on `mychart.py` by hand, start the mock and point the scraper at it
with `MYCHART_BASE_URL`. In one shell:

```bash
python3 .claude/skills/run-agent/mock_mychart.py --port 8799
```

In another (the scraper pauses at MFA until you write the code file):

```bash
MYCHART_BASE_URL=http://127.0.0.1:8799/mychart \
MYCHART_EU_USER=x MYCHART_EU_PASS=x \
python3 agent/mychart.py --account eu --out /tmp/run-out &
# when status.json shows "waiting_mfa":
echo 246810 > /tmp/run-out/mfa_code.txt
```

## Run against the real MyChart

Only works where the environment can reach `mychart.uihealthcare.org` and the
`MYCHART_*` credentials are set (see `agent/README.md`). Same command without
`MYCHART_BASE_URL`. The full weekly rotation (both accounts → Google Calendar)
is the `/check-medico` skill, not this one.

## Failure-mode exit codes (verified)

`agent/mychart.py` exits with a distinct code per failure, so the driver and
`/check-medico` can react. These were reproduced in this environment:

- Missing `MYCHART_*` env vars → exit **2** (`missing env vars ...`).
- Network policy blocks the portal → exit **4** (`network blocked by
  environment policy`) — this is what the *live* URL does here.
- MFA code never supplied within 5 min → exit **3**.

## Gotchas

- **The scraper blocks on MFA by design.** It polls `<out>/mfa_code.txt` for up
  to 5 minutes. If you run it directly and never write that file, it exits 3.
  The driver writes the file automatically.
- **`MYCHART_BASE_URL` override.** The mock is reached only because the scraper
  honors this env var over `config.json`. It also appends
  `config.login_path` (`/Authentication/Login`), so the mock serves that exact
  route (lowercase `mychart` in the path — matches the real portal).
- **Chromium version skew.** `mychart.py` falls back to the browser binary in
  `PLAYWRIGHT_BROWSERS_PATH` if the pip `playwright` package's bundled version
  doesn't match. If launch fails anyway, check that dir exists.
- **Selectors are best-effort.** The mock mirrors the selectors the scraper
  targets (`#Login`, password field, `#submit`, numeric code input, a "Past"
  tab). The real Epic portal may differ; a green driver proves the scraper
  *logic*, not that UIHC hasn't changed its DOM.

## Troubleshooting

- `ModuleNotFoundError: playwright` → `pip install -r agent/requirements.txt`
  (may need `--default-timeout 120` on a slow mirror).
- Driver hangs at `[3/5] waiting for MFA` → the scraper never reached the MFA
  page; check the mock started (its stdout line) and that the port is free.
- `network blocked by environment policy` when hitting the real portal → add
  `mychart.uihealthcare.org` to the environment's network allow-list.
