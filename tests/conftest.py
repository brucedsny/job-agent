"""Shared test doubles (offline: no network, no API key)."""

from __future__ import annotations

import pytest

from src.config import get_settings
from src.crm.repository import CRM
from src.llm import LLMResult, SpendCapExceeded
from src.models import (
    CandidateProfile,
    ContactInfo,
    Experience,
    FitResult,
    JobExtraction,
    SkillItem,
)
from src.orchestrator import Orchestrator


class FakeLLM:
    """Duck-typed LLMClient returning canned values per schema."""

    def __init__(self, fail_after: int | None = None, overrides: dict | None = None) -> None:
        self.calls = 0
        self.fail_after = fail_after
        self.overrides = overrides or {}
        self.settings = get_settings()

    def structured(self, model, schema, system, user, **kw):
        self.calls += 1
        if self.fail_after is not None and self.calls > self.fail_after:
            raise SpendCapExceeded("cap")
        if schema in self.overrides:
            val = self.overrides[schema]
        elif schema is JobExtraction:
            val = JobExtraction(title="Eng", company="Acme", must_haves=["Python"])
        elif schema is FitResult:
            val = FitResult(interview_probability=0.8, score=80, rationale="ok")
        else:
            val = schema()
        return LLMResult(value=val, model=model, cost_usd=0.001)


def make_profile() -> CandidateProfile:
    return CandidateProfile(
        contact=ContactInfo(name="Maria Silva", email="m@x.com", location="SP"),
        summary="Backend em Python.",
        experiences=[Experience(company="Acme", title="Eng", start="2021-03",
                                bullets=["Reduziu latência p95 para 180ms."],
                                skills=["Python", "FastAPI"])],
        skills=[SkillItem(name="Python")],
    )


@pytest.fixture
def make_orch(tmp_path):
    def _make(llm=None, **kw) -> Orchestrator:
        return Orchestrator(CRM(tmp_path / "crm.sqlite"), make_profile(), get_settings(),
                            llm=llm or FakeLLM(),
                            fetcher=lambda url: "<p>Backend Engineer. Python required.</p>", **kw)
    return _make
