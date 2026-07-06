#!/usr/bin/env python3
"""Minimal fake MyChart (Epic) portal for driving agent/mychart.py offline.

Serves an Epic-shaped login page, an email-code MFA challenge, and Visits
pages (upcoming + past) so the real scraper can be exercised end-to-end with
no live portal, no credentials, and no network egress. The HTML mirrors the
selectors mychart.py looks for (#Login, password input, #submit, a numeric
code field, a "Past" tab).

Usage:
    python mock_mychart.py --port 8799
Routes (all under /mychart):
    GET  /mychart/Authentication/Login   login form
    POST /mychart/Authentication/Login   -> 302 /mychart/mfa
    GET  /mychart/mfa                     code form (accepts any >=4 digits)
    POST /mychart/mfa                     -> 302 /mychart  (logged in)
    GET  /mychart                         home (has "Log Out" + Visits link)
    GET  /mychart/Visits                  upcoming visits (+ Past tab)
    GET  /mychart/Visits?tab=past         past visits
"""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>
</head><body>{body}</body></html>"""

LOGIN_BODY = """
<h1>UI Health Care MyChart</h1>
<form method="POST" action="/mychart/Authentication/Login">
  <label>MyChart Username <input type="text" id="Login" name="Login"></label>
  <label>Password <input type="password" id="Password" name="Password"></label>
  <button type="submit" id="submit">Sign In</button>
</form>
<a href="#">Forgot Username?</a> <a href="#">Forgot Password?</a>
"""

MFA_BODY = """
<h1>Verify your identity</h1>
<p>We sent a security code to your email. Enter the verification code below.</p>
<form method="POST" action="/mychart/mfa">
  <input type="text" inputmode="numeric" id="code" name="code" autocomplete="one-time-code">
  <label><input type="checkbox" id="trustDevice" name="remember"> Trust this device</label>
  <button type="submit">Verify</button>
</form>
"""

HOME_BODY = """
<h1>Welcome to MyChart</h1>
<nav><a href="/mychart/Visits">Visits</a> <a href="#">Messages</a>
<a href="/mychart/Authentication/Logout">Log Out</a></nav>
<p>You have upcoming appointments. Review your Visits.</p>
"""

VISITS_UPCOMING_BODY = """
<h1>Visits</h1>
<div role="tablist">
  <button role="tab" aria-selected="true">Upcoming</button>
  <a role="tab" href="/mychart/Visits?tab=past">Past</a>
</div>
<a href="/mychart/Authentication/Logout">Log Out</a>
<ul id="upcoming">
  <li>
    <strong>Cardiology</strong> — Dr. Aisha Khan<br>
    Tuesday August 18, 2026 &nbsp; 9:30 AM CDT<br>
    UIHC Heart & Vascular Center, 200 Hawkins Dr, Iowa City, IA
  </li>
  <li>
    <strong>Dermatology</strong> — Dr. Lucas Meyer<br>
    Thursday September 3, 2026 &nbsp; 2:00 PM CDT<br>
    UIHC Dermatology Clinic, 200 Hawkins Dr, Iowa City, IA
  </li>
</ul>
"""

VISITS_PAST_BODY = """
<h1>Visits</h1>
<div role="tablist">
  <a role="tab" href="/mychart/Visits">Upcoming</a>
  <button role="tab" aria-selected="true">Past</button>
</div>
<a href="/mychart/Authentication/Logout">Log Out</a>
<ul id="past">
  <li>
    <strong>Cardiology</strong> — Dr. Aisha Khan<br>
    Monday February 10, 2025 &nbsp; 10:00 AM CST &nbsp; Completed
  </li>
  <li>
    <strong>Primary Care</strong> — Dr. Nina Alvarez<br>
    Wednesday March 12, 2025 &nbsp; 8:15 AM CDT &nbsp; Completed<br>
    To schedule a follow-up call (319) 384-8442.
  </li>
  <li>
    <strong>Ophthalmology</strong> — Dr. Omar Reyes<br>
    Friday November 8, 2024 &nbsp; 1:45 PM CST &nbsp; Completed
  </li>
</ul>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, title, body, status=200, location=None):
        html = PAGE.format(title=title, body=body).encode()
        self.send_response(status)
        if location:
            self.send_header("Location", location)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def log_message(self, *args):  # keep the test output quiet
        pass

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/") or "/mychart"
        if path in ("/mychart/Authentication/Login", "/mychart/authentication/login"):
            self._send("Login", LOGIN_BODY)
        elif path == "/mychart/mfa":
            self._send("Verify", MFA_BODY)
        elif path == "/mychart/Visits":
            if "tab=past" in self.path:
                self._send("Visits - Past", VISITS_PAST_BODY)
            else:
                self._send("Visits", VISITS_UPCOMING_BODY)
        elif path in ("/mychart", "/mychart/home"):
            self._send("MyChart", HOME_BODY)
        else:
            self._send("Not Found", "<h1>404</h1>", status=404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        path = self.path.split("?")[0].rstrip("/")
        if path in ("/mychart/Authentication/Login", "/mychart/authentication/login"):
            self._send("Redirect", "", status=302, location="/mychart/mfa")
        elif path == "/mychart/mfa":
            self._send("Redirect", "", status=302, location="/mychart")
        else:
            self._send("Not Found", "<h1>404</h1>", status=404)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8799)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"mock MyChart on http://127.0.0.1:{args.port}/mychart", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
