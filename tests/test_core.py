"""Models, CRM and the deterministic parts of the agents."""

from __future__ import annotations

from src.agents.discovery import (
    canonicalize_url,
    discover_ashby,
    discover_lever,
    parse_ashby_jobs,
    parse_greenhouse_jobs,
    parse_lever_postings,
)
from src.agents.document import render_html
from src.agents.extraction import detect_apply_mode, html_to_text
from src.agents.tailor import deterministic_unsupported
from src.crm.repository import CRM
from src.models import (
    ApplyMode,
    FitAssessment,
    JobLead,
    JobStatus,
    ResumeBullet,
    TailoredExperience,
    TailoredResume,
)

from .conftest import make_profile


def test_fact_corpus_is_normalized():
    corpus = make_profile().fact_corpus()
    assert "acme" in corpus and "180ms" in corpus and "maria silva" in corpus


def test_hash_is_normalized():
    assert JobLead.hash_content("Backend  Engineer") == JobLead.hash_content("backend engineer")


def test_crm_dedup_status_and_funnel(tmp_path):
    crm = CRM(tmp_path / "crm.sqlite")
    lead = JobLead(source="manual", url="https://x.com/jobs/1?utm_source=a")
    assert crm.add_lead(lead, "https://x.com/jobs/1")
    assert not crm.add_lead(JobLead(source="manual", url="https://x.com/jobs/1"), "https://x.com/jobs/1")
    crm.set_status(lead.id, JobStatus.RANKED)
    crm.save_fit(FitAssessment(job_id=lead.id, interview_probability=0.7, score=70))
    assert crm.get_status(lead.id) == JobStatus.RANKED
    assert crm.get_fit(lead.id).score == 70
    assert crm.funnel() == {"ranked": 1}


def test_canonicalize_url():
    assert canonicalize_url("HTTPS://X.com/Jobs/1/?utm_source=f&q=py#x") == "https://x.com/Jobs/1?q=py"


def test_source_parsers():
    gh = parse_greenhouse_jobs({"jobs": [
        {"id": 1, "title": "Backend Engineer", "absolute_url": "https://b/1", "content": "Py &amp; Go"},
        {"id": 2, "title": "Designer", "absolute_url": "https://b/2"}]}, "acme", query="backend")
    assert [x.title for x in gh] == ["Backend Engineer"] and gh[0].source == "greenhouse:acme"

    lv = parse_lever_postings([{"id": "a", "text": "Python Eng", "hostedUrl": "https://l/a"},
                               {"id": "b", "text": "Sales"}], "acme", query="python")
    assert len(lv) == 1 and lv[0].source == "lever:acme"

    ab = parse_ashby_jobs({"jobs": [{"id": "j", "title": "Eng", "jobUrl": "https://a/j"}]}, "acme")
    assert ab[0].source == "ashby:acme"

    assert discover_lever("acme", fetch_json=lambda u: [{"id": "x", "text": "E", "hostedUrl": "u"}])
    assert discover_ashby("acme", fetch_json=lambda u: {"jobs": [{"id": "x", "title": "E"}]})


def test_html_to_text_and_apply_mode():
    assert "Olá mundo" in html_to_text("<p>Olá <b>mundo</b></p><script>x()</script>")
    mode, _ = detect_apply_mode(JobLead(source="m", url="https://boards.greenhouse.io/a/jobs/1"), "")
    assert mode == ApplyMode.API
    mode, target = detect_apply_mode(JobLead(source="m", url="https://x.com/v"),
                                     '<a href="mailto:jobs@x.com">')
    assert mode == ApplyMode.EMAIL and target == "jobs@x.com"


def test_guard_regression():
    corpus = "reduziu a latencia para 180ms em python desde 2021"
    assert deterministic_unsupported("Aumentou vendas em 95%", corpus)       # invented metric
    assert deterministic_unsupported("Desde 2015 em Python", corpus)          # invented year
    assert not deterministic_unsupported("Latência caiu para 180ms", corpus)  # real metric
    assert not deterministic_unsupported("Trabalha com Python desde 2021", corpus)
    assert not deterministic_unsupported("Liderou o time de backend", corpus)  # no numbers


def test_render_html_is_ats_safe_and_escaped():
    html = render_html(TailoredResume(
        job_id="j", name="Maria <script>", headline="Backend", summary="Resumo",
        experiences=[TailoredExperience(company="Acme", title="Eng", dates="2021–",
                                        bullets=[ResumeBullet(text="Fez X")])],
        skills=["Python"], education_lines=["BSc — USP"]))
    assert "Experiência" in html and "Competências" in html and "Fez X" in html
    assert "<table" not in html and "<script>" not in html
