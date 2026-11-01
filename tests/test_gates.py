"""Safety gates: Gate B (approval), Gate C (browser consent), kill-switch, policy."""

from __future__ import annotations

import pytest

from src.agents.ats_api import parse_greenhouse_ref, submit_greenhouse, submit_via_ats
from src.agents.browser import BrowserConsentRequired, submit_via_browser
from src.agents.submission import SubmissionBlocked, submit
from src.config import Settings, get_settings
from src.models import (
    ApplicationDraft,
    ApplyMode,
    FitAssessment,
    JobLead,
    JobStatus,
    StructuredJob,
)
from src.policy import KillSwitchEngaged, evaluate_policy, is_killed

from .conftest import make_profile


def _job(mode=ApplyMode.EMAIL, target="jobs@acme.com", **kw) -> StructuredJob:
    return StructuredJob(lead_id="j1", title="Eng", company="acme", apply_mode=mode,
                         apply_target=target, **kw)


def _draft(status=JobStatus.APPROVED, **kw) -> ApplicationDraft:
    return ApplicationDraft(job_id="j1", resume_pdf_path="/nonexistent.pdf", status=status, **kw)


# --- Gate B --------------------------------------------------------------
def test_gate_b_blocks_unapproved():
    with pytest.raises(SubmissionBlocked):
        submit(_draft(JobStatus.PENDING_APPROVAL), _job(), make_profile(), get_settings())


def test_gate_b_blocks_blocking_issues_even_if_approved():
    with pytest.raises(SubmissionBlocked):
        submit(_draft(blocking_issues=["unsupported claim"]), _job(), make_profile(), get_settings())


def test_caps_block():
    with pytest.raises(SubmissionBlocked):
        submit(_draft(), _job(), make_profile(), get_settings(), company_count=1)


def test_email_without_smtp_saves_eml(tmp_path, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "smtp_host", None)
    monkeypatch.setattr(s, "data_dir", tmp_path)
    result = submit(_draft(), _job(), make_profile(), s)
    assert not result.success and ".eml" in result.error
    assert (s.outbox_dir / "j1.eml").exists()


# --- ATS API -------------------------------------------------------------
class _Resp:
    def __init__(self, code, text=""):
        self.status_code, self.text = code, text


GH = "https://boards.greenhouse.io/acme/jobs/123"


def test_greenhouse_ref_and_submit():
    assert parse_greenhouse_ref(GH) == ("acme", "123")
    sent = {}

    def post(url, headers, data, files):
        sent.update(url=url, auth=headers["Authorization"], data=data)
        return _Resp(201)

    ok = submit_greenhouse(_job(ApplyMode.API, GH), make_profile(), _draft(), "KEY", post)
    assert ok.success and sent["url"].endswith("/boards/acme/jobs/123")
    assert sent["auth"].startswith("Basic ") and sent["data"]["last_name"] == "Silva"
    bad = submit_greenhouse(_job(ApplyMode.API, GH), make_profile(), _draft(), "KEY",
                            lambda *a: _Resp(422, "bad"))
    assert not bad.success and "422" in bad.error


def test_api_without_key_falls_back_to_manual():
    s = get_settings()
    assert submit_via_ats(_job(ApplyMode.API, GH), make_profile(), _draft(), s) is None
    r = submit(_draft(), _job(ApplyMode.API, GH), make_profile(), s)
    assert not r.success and "manual" in r.error.lower()


# --- Gate C --------------------------------------------------------------
def test_browser_requires_gate_c():
    for consent in (True, False):
        with pytest.raises(BrowserConsentRequired):
            submit_via_browser(_job(ApplyMode.BROWSER, "https://x"), make_profile(), _draft(),
                               get_settings(), consent=consent)


# --- Kill-switch ---------------------------------------------------------
def test_kill_switch_flag_and_file(tmp_path):
    assert is_killed(Settings(kill_switch=True))
    s = Settings(data_dir=tmp_path)
    assert not is_killed(s)
    (tmp_path / "STOP").write_text("x")
    assert is_killed(s)


def test_kill_switch_blocks_orchestrator(make_orch, monkeypatch, tmp_path):
    s = get_settings()
    monkeypatch.setattr(s, "data_dir", tmp_path)
    orch = make_orch()
    lead = JobLead(source="m", url="https://x.com/1")
    orch.crm.add_lead(lead, lead.url)
    s.stop_file.write_text("stop")
    with pytest.raises(KillSwitchEngaged):
        orch.extract(lead.id)
    s.stop_file.unlink()
    orch.extract(lead.id)
    assert orch.crm.get_status(lead.id) == JobStatus.EXTRACTED


# --- Policy --------------------------------------------------------------
def _fit(score=80, missing=None) -> FitAssessment:
    return FitAssessment(job_id="j", interview_probability=score / 100, score=score,
                         missing_must=missing or [])


def test_policy_rules():
    job = _job()
    assert evaluate_policy(job, _fit(80), Settings(policy_min_score=75)).passes
    assert not evaluate_policy(job, _fit(80), Settings(policy_min_score=85)).passes
    assert not evaluate_policy(job, _fit(90, ["K8s"]), Settings()).passes
    assert not evaluate_policy(job, _fit(90), Settings(policy_company_blocklist=["acme"])).passes
    assert not evaluate_policy(job, _fit(90), Settings(policy_company_allowlist=["other"])).passes
    assert not evaluate_policy(job, _fit(95), Settings(), has_open_questions=True).passes
    assert not evaluate_policy(_job(salary_max=50_000), _fit(95),
                               Settings(policy_salary_floor=80_000)).passes
