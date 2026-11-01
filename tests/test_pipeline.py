"""Batch pipeline, autopilot (stops at Gate B), funnel learning, cover guard, LLM fallback."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import src.agents.document as docmod
from src.agents.cover import CoverOutput, generate_cover_letter
from src.agents.document import AtsReport
from src.config import get_settings
from src.crm.repository import CRM
from src.learning import callback_rates, score_adjustment
from src.llm import LLMClient, LLMError
from src.models import (
    ApplicationDraft,
    FitAssessment,
    JobExtraction,
    JobLead,
    JobStatus,
    Seniority,
    StructuredJob,
    TailoredResume,
)

from .conftest import FakeLLM, make_profile


def _add(crm, n, start=0):
    ids = []
    for i in range(start, start + n):
        lead = JobLead(source="m", url=f"https://x.com/{i}")
        crm.add_lead(lead, lead.url)
        ids.append(lead.id)
    return ids


@pytest.fixture
def fake_pdf(monkeypatch):
    monkeypatch.setattr(docmod, "render_pdf",
                        lambda resume, out: (Path(out).write_bytes(b"%PDF"), "fake")[1])
    monkeypatch.setattr(docmod, "validate_ats", lambda p: AtsReport(
        passed=True, char_count=500, has_images=False, found_headings=["RESUMO"], issues=[]))


def test_batch_extract_and_rank(make_orch):
    orch = make_orch()
    _add(orch.crm, 2)
    assert orch.extract_all() == {"processed": 2, "stopped_by_spend_cap": 0}
    assert orch.rank_all()["processed"] == 2
    assert orch.crm.funnel() == {"ranked": 2}


def test_spend_cap_stops_batch(make_orch):
    orch = make_orch(FakeLLM(fail_after=1))
    _add(orch.crm, 2)
    assert orch.extract_all() == {"processed": 1, "stopped_by_spend_cap": 1}


def test_approve_all_skips_blocked(make_orch):
    orch = make_orch()
    clean, blocked = _add(orch.crm, 2)
    for jid, issues in ((clean, []), (blocked, ["unsupported claim"])):
        orch.crm.save_draft(ApplicationDraft(job_id=jid, resume_pdf_path="x.pdf",
                                             blocking_issues=issues))
        orch.crm.set_status(jid, JobStatus.PENDING_APPROVAL)
    assert orch.approve_all() == [clean]
    assert orch.crm.get_status(blocked) == JobStatus.PENDING_APPROVAL


def test_autopilot_prepares_and_stops_at_gate_b(make_orch, fake_pdf):
    orch = make_orch()
    (jid,) = _add(orch.crm, 1)
    r = orch.autopilot()
    assert r == {"prepared": [jid], "skipped": [], "stopped": None}
    assert orch.crm.get_status(jid) == JobStatus.PENDING_APPROVAL  # never submitted


def test_autopilot_skips_by_policy(make_orch, monkeypatch):
    monkeypatch.setattr(get_settings(), "policy_min_score", 95)
    orch = make_orch()
    (jid,) = _add(orch.crm, 1)
    r = orch.autopilot()
    assert r["prepared"] == [] and r["skipped"][0]["id"] == jid


def test_funnel_learning(tmp_path):
    crm = CRM(tmp_path / "crm.sqlite")
    job = StructuredJob(lead_id="cur", title="Eng", company="x", seniority=Seniority.SENIOR)
    fit = FitAssessment(job_id="cur", interview_probability=0.8, score=80)
    assert score_adjustment(job, fit, crm)[0] == 0  # no history

    for i in range(6):
        senior = i < 3
        lead = JobLead(source="greenhouse:x", url=f"https://x.com/{i}")
        crm.add_lead(lead, lead.url)
        crm.save_job(StructuredJob(lead_id=lead.id, title="Eng", company="x",
                                   seniority=Seniority.SENIOR if senior else Seniority.JUNIOR))
        crm.save_fit(FitAssessment(job_id=lead.id, interview_probability=0.8, score=80))
        crm.record_outcome(lead.id, "applied")
        if senior:
            crm.record_outcome(lead.id, "callback")

    rates = callback_rates(crm)
    assert rates["seniority:senior"]["rate"] == 1.0
    assert rates["seniority:junior"]["rate"] == 0.0
    delta, note = score_adjustment(job, fit, crm)
    assert delta == 5 and "seniority:senior" in note


def test_cover_letter_guard():
    job = StructuredJob(lead_id="j", title="Eng", company="Acme")
    resume = TailoredResume(job_id="j", name="Maria")
    fake = FakeLLM(overrides={CoverOutput: CoverOutput(text="Aumentei a receita em 250%. Uso Python.")})
    _, flagged, _ = generate_cover_letter(job, make_profile(), resume, fake, get_settings())
    assert flagged == ["Aumentei a receita em 250%."]
    fake = FakeLLM(overrides={CoverOutput: CoverOutput(text="Trabalho com Python.")})
    assert generate_cover_letter(job, make_profile(), resume, fake, get_settings())[1] == []


class _ParseClient:
    """Fake Anthropic client: first model fails, fallback succeeds."""

    def __init__(self, fail_models):
        self.fail_models, self.seen = fail_models, []
        self.messages = self

    def parse(self, **kw):
        self.seen.append(kw["model"])
        if kw["model"] in self.fail_models:
            raise RuntimeError("overloaded")
        return SimpleNamespace(parsed_output=JobExtraction(title="t", company="c"),
                               usage=SimpleNamespace(input_tokens=1000, output_tokens=100))


def test_llm_fallback_and_cost():
    client = _ParseClient({"claude-sonnet-4-6"})
    llm = LLMClient(get_settings(), client=client)
    r = llm.structured("claude-sonnet-4-6", JobExtraction, "s", "u")
    assert client.seen == ["claude-sonnet-4-6", "claude-haiku-4-5"]
    assert r.model == "claude-haiku-4-5" and r.cost_usd == pytest.approx(0.0015)

    with pytest.raises(LLMError):
        LLMClient(get_settings(), client=_ParseClient({"claude-haiku-4-5"})).structured(
            "claude-haiku-4-5", JobExtraction, "s", "u")
