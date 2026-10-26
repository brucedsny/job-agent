#!/usr/bin/env python3
"""Minimal fake MyChart (Epic) portal for driving agent/mychart.py offline.

Mirrors the live UIHC flow observed on 2026-10-26: a two-step login
(username -> Continue -> password on the same URL), the "Verify your
identity" page that asks how to send the code (#textCode / #emailCode),
the code page (#twofactorcode, #rememberMe, #submitSecondaryValidation),
then Home ("Welcome, <name>!") and the Visits page. No live portal,
credentials or network egress are involved.

Usage:
    python mock_mychart.py --port 8799 [--patient Clea]
Routes (all under /mychart):
    GET  /mychart/Authentication/Login                 username step
    POST /mychart/Authentication/Login  step=user      -> password step
    POST /mychart/Authentication/Login  step=password  -> 302 SecondaryValidation
    GET  /mychart/Authentication/SecondaryValidation   choose text/email
    POST /mychart/Authentication/SecondaryValidation   method=email -> code page
                                                       code=...     -> "Loading" page,
                                                       refreshes to Home after 2 s
    GET  /mychart/Home                                 "Welcome, <name>!"
    GET  /mychart/Visits                               upcoming visits (+ Past tab)
    GET  /mychart/Visits?tab=past                      past visits
"""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

PATIENT = "Clea"

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>
</head><body>{body}</body></html>"""

LOGIN_USER_BODY = """
<p>Your Username is not case sensitive, but your password is.</p>
<form method="POST" action="/mychart/Authentication/Login">
  <input type="hidden" name="step" value="user">
  <label>MyChart Username or Epic ID <input type="text" id="Login" name="Login"></label>
  <a href="#">Forgot login information?</a>
  <input type="submit" id="submit" name="submit" value="Continue">
</form>
"""

LOGIN_PASSWORD_BODY = """
<p>Log in with your password for UI Health Care and the Community Connect Practices</p>
<form method="POST" action="/mychart/Authentication/Login">
  <input type="hidden" name="step" value="password">
  <label>MyChart Username <input type="text" id="Login" name="Login" value="{user}"></label>
  <label>Password <input type="password" id="Password" name="Password"></label>
  <a href="#">Forgot login information?</a>
  <input type="submit" id="submit" name="submit" value="Log in">
</form>
"""

CHOOSE_BODY = """
<h1>Verify your identity</h1>
<p>You will now be required to enter a one-time use security code to verify your identity.</p>
<p>How would you like to receive the code?</p>
<form method="POST" action="/mychart/Authentication/SecondaryValidation">
  <button type="submit" id="textCode" name="method" value="text">Text to my phone</button>
  <button type="submit" id="emailCode" name="method" value="email">Send to my email</button>
</form>
"""

CODE_BODY = """
<h1>Verify your identity</h1>
<p>We've sent a security code to br****y@gmail.com.</p>
<p>Enter your code below to continue.</p>
<form method="POST" action="/mychart/Authentication/SecondaryValidation">
  <label for="twofactorcode">Enter Code</label>
  <input type="text" id="twofactorcode" name="twofactorcode">
  <input type="checkbox" id="rememberMe" name="RememberMe" checked>
  <label for="rememberMe">Trust this device</label>
  <button type="submit" id="submitSecondaryValidation">Verify</button>
  <button type="button" id="resendCode">Resend code</button>
</form>
"""

HOME_BODY = """
<h1>Welcome, {patient}!</h1>
<nav><a href="/mychart/Scheduling">Schedule an Appointment</a> <a href="#">Messages</a>
<a href="/mychart/Visits">Visits</a> <a href="#">Test Results</a> <a href="#">Medications</a>
<a href="/mychart/Authentication/Logout">Log Out</a></nav>
<p>Appointment on Tuesday August 18, 2026.</p>
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

    def _path(self):
        return (self.path.split("?")[0].rstrip("/") or "/mychart").lower()

    def do_GET(self):
        path = self._path()
        if path == "/mychart/authentication/login":
            self._send("MyChart - Login Page", LOGIN_USER_BODY)
        elif path == "/mychart/authentication/secondaryvalidation":
            self._send("MyChart - Extra Security Required", CHOOSE_BODY)
        elif path == "/mychart/visits":
            if "tab=past" in self.path:
                self._send("Visits - Past", VISITS_PAST_BODY)
            else:
                self._send("MyChart - Appointments and Visits", VISITS_UPCOMING_BODY)
        elif path in ("/mychart", "/mychart/home"):
            self._send("MyChart - Home", HOME_BODY.format(patient=PATIENT))
        else:
            self._send("Not Found", "<h1>404</h1>", status=404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        form = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode()).items()}
        path = self._path()
        if path == "/mychart/authentication/login":
            if form.get("step") == "user":
                self._send("MyChart - Login Page", LOGIN_PASSWORD_BODY.format(user=form.get("Login", "")))
            else:
                self._send("Redirect", "", status=302, location="/mychart/Authentication/SecondaryValidation")
        elif path == "/mychart/authentication/secondaryvalidation":
            if form.get("method") == "email":
                self._send("MyChart - Extra Security Required", CODE_BODY)
            elif form.get("twofactorcode"):
                # Live portal: an interstitial stays on this URL before Home.
                self._send(
                    "Loading https://mychart.uihealthcare.org/MyChart/inside.asp",
                    '<meta http-equiv="refresh" content="2;url=/mychart/Home"><p>Loading...</p>',
                )
            else:
                self._send("MyChart - Extra Security Required", CHOOSE_BODY)
        else:
            self._send("Not Found", "<h1>404</h1>", status=404)


def main():
    global PATIENT
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8799)
    parser.add_argument("--patient", default="Clea")
    args = parser.parse_args()
    PATIENT = args.patient
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"mock MyChart on http://127.0.0.1:{args.port}/mychart", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
