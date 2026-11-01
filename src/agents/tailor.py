"""Agent 4 — Resume Tailor (Opus) + anti-fabrication guard.

The tailored resume may only reorder, rephrase and emphasize facts that exist in
the master profile. Two guard layers: deterministic (numbers/metrics absent from
the profile) and an LLM fact-checker. Flagged bullets get grounded=False and
block progress until human review (Gate D).
"""

from __future__ import annotations

import re

from ..config import Settings
from ..llm import LLMClient
from ..models import (
    CandidateProfile,
    FactCheckOutput,
    ResumeBullet,
    StructuredJob,
    TailoredExperience,
    TailoredResume,
    TailorOutput,
    normalize_text,
)

_NUM_RE = re.compile(r"\$?\d+(?:[.,]\d+)?%?")

_SYSTEM = (
    "You tailor a candidate's master resume to ONE specific job.\n"
    "ABSOLUTE RULE: use only facts present in the profile. NEVER invent or inflate "
    "companies, titles, dates, degrees, tools or metrics. You may reorder, rewrite and "
    "emphasize — never create new facts.\nFor each bullet fill 'source_ref' with the "
    "profile experience/fact that supports it. If something has no support, do NOT write "
    "it. Align vocabulary to the job only when true. In 'diff_notes', briefly explain "
    "what was emphasized and why."
)

_GUARD_SYSTEM = (
    "You are a strict fact-checker. You get (A) the candidate's verifiable facts and (B) "
    "bullets of a tailored resume. List in 'unsupported_claims' ANY statement in B not "
    "supported by A (metrics, titles, dates, tools, achievements). Do not list faithful "
    "rephrasings. Quote the problematic text."
)


def profile_facts(profile: CandidateProfile) -> str:
    lines = [f"Name: {profile.contact.name}", f"Summary: {profile.summary}"]
    for e in profile.experiences:
        lines.append(f"[{e.title} @ {e.company} ({e.start}–{e.end or 'present'})]")
        lines += [f"  - {b}" for b in e.bullets]
        if e.skills:
            lines.append(f"  skills: {', '.join(e.skills)}")
    lines += [f"[Education] {ed.degree} {ed.field or ''} @ {ed.institution}" for ed in profile.education]
    lines.append("Skills: " + ", ".join(profile.skill_names()))
    if profile.certifications:
        lines.append("Certifications: " + ", ".join(profile.certifications))
    return "\n".join(lines)


def deterministic_unsupported(text: str, corpus: str) -> bool:
    """True if `text` contains a number/metric (2+ digits) absent from the corpus."""
    corpus_digits = re.sub(r"[^\d]", " ", corpus)
    for tok in _NUM_RE.findall(text):
        digits = re.sub(r"[^\d]", "", tok)
        if len(digits) >= 2 and digits not in corpus_digits:
            return True
    return False


def tailor_resume(job: StructuredJob, profile: CandidateProfile, llm: LLMClient,
                  settings: Settings) -> tuple[TailoredResume, float]:
    facts = profile_facts(profile)
    user = (
        "=== CANDIDATE FACTS (only allowed source) ===\n" + facts + "\n\n=== JOB ===\n"
        f"{job.title} @ {job.company} ({job.seniority.value})\n"
        f"Must-haves: {', '.join(job.must_haves) or '—'}\n"
        f"Nice-to-haves: {', '.join(job.nice_to_haves) or '—'}\n\n"
        "Tailor the resume to this job following the ABSOLUTE RULE."
    )
    result = llm.structured(settings.model_for("tailor"), TailorOutput, _SYSTEM, user)
    out: TailorOutput = result.value
    total_cost = result.cost_usd
    corpus = profile.fact_corpus()

    flagged: list[str] = []
    experiences: list[TailoredExperience] = []
    all_bullets: list[str] = []
    for exp in out.experiences:
        bullets = []
        for b in exp.bullets:
            grounded = not deterministic_unsupported(b.text, corpus)
            if not grounded:
                flagged.append(b.text)
            bullets.append(ResumeBullet(text=b.text, source_ref=b.source_ref, grounded=grounded))
            all_bullets.append(b.text)
        experiences.append(TailoredExperience(company=exp.company, title=exp.title,
                                              dates=exp.dates, bullets=bullets))

    if all_bullets:
        guard_user = ("=== (A) CANDIDATE FACTS ===\n" + facts + "\n\n=== (B) TAILORED BULLETS ===\n"
                      + "\n".join(f"- {t}" for t in all_bullets))
        guard = llm.structured(settings.model_for("tailor"), FactCheckOutput, _GUARD_SYSTEM, guard_user)
        total_cost += guard.cost_usd
        for claim in guard.value.unsupported_claims:
            if claim not in flagged:
                flagged.append(claim)
            nclaim = normalize_text(claim)
            for exp in experiences:
                for rb in exp.bullets:
                    if nclaim and nclaim in normalize_text(rb.text):
                        rb.grounded = False

    c = profile.contact
    return TailoredResume(
        job_id=job.lead_id, name=c.name,
        contact_line=" · ".join(x for x in (c.location, c.email, c.phone) if x),
        headline=out.headline, summary=out.summary, experiences=experiences, skills=out.skills,
        education_lines=[f"{ed.degree} {ed.field or ''} — {ed.institution}".strip()
                         for ed in profile.education],
        diff_notes=out.diff_notes, flagged_unsupported=flagged,
    ), total_cost
