"""Job Search Agent CLI (Typer).

Typical flow:
  job-agent init-profile          # create data/profile/master.yaml (fill in REAL data)
  job-agent discover --url ...    # or --greenhouse/--lever/--ashby/--all
  job-agent run <job_id>          # 2->6, stops at Gate B
  job-agent review <job_id>       # Gate B preview
  job-agent approve <job_id>      # explicit human approval
  job-agent submit <job_id>       # API/email; browser needs --consent
"""

from __future__ import annotations

import typer

from . import learning, policy
from .agents import discovery as disc
from .config import get_settings
from .crm.repository import CRM
from .llm import LLMClient
from .models import JobStatus
from .orchestrator import Orchestrator
from .profile import init_profile_example, load_profile

app = typer.Typer(help="Job Search Agent — human in charge of every application.")

OUTCOMES = {"applied", "callback", "interview", "offer", "rejected", "ghosted"}


def _crm() -> CRM:
    return CRM(get_settings().db_path)


def _orch() -> Orchestrator:
    s = get_settings()
    return Orchestrator(CRM(s.db_path), load_profile(settings=s), s, LLMClient(s))


def _fail(msg: str) -> None:
    typer.echo(msg, err=True)
    raise typer.Exit(1)


@app.command()
def init_profile() -> None:
    """Create data/profile/master.yaml from the example (if missing)."""
    typer.echo(f"Profile at: {init_profile_example()}\nFill it with REAL data before continuing.")


@app.command()
def discover(
    url: str = typer.Option(None, help="Job URL (manual source)."),
    greenhouse: str = typer.Option(None, help="Greenhouse board token."),
    lever: str = typer.Option(None, help="Lever company slug."),
    ashby: str = typer.Option(None, help="Ashby board name."),
    all_sources: bool = typer.Option(False, "--all", help="All sources from config."),
    query: str = typer.Option(None, help="Title filter."),
) -> None:
    """1 Discover jobs."""
    crm = _crm()
    leads = []
    if url:
        leads.append(disc.discover_from_url(url))
    if greenhouse:
        leads += disc.discover_greenhouse(greenhouse, query)
    if lever:
        leads += disc.discover_lever(lever, query)
    if ashby:
        leads += disc.discover_ashby(ashby, query)
    if all_sources:
        leads += disc.discover_all(get_settings(), query)
    added = sum(int(crm.add_lead(ld, disc.canonicalize_url(ld.url))) for ld in leads)
    typer.echo(f"{added} new job(s) added ({len(leads)} found).")


@app.command(name="list")
def list_leads(status: str = typer.Option(None, help="Filter by status.")) -> None:
    """List jobs in the CRM."""
    crm = _crm()
    for lead, st in crm.list_leads(JobStatus(status) if status else None):
        fit = crm.get_fit(lead.id)
        score = f"score={fit.score}" if fit else "score=—"
        typer.echo(f"{lead.id}  [{st.value:16}] {score:10} {lead.title or lead.url}")


@app.command()
def extract(job_id: str = typer.Argument(None), all_leads: bool = typer.Option(False, "--all")) -> None:
    """2 Structure the job description (one or --all)."""
    orch = _orch()
    if all_leads:
        typer.echo(f"Batch: {orch.extract_all()}")
    elif job_id:
        orch.extract(job_id)
        typer.echo(f"Extracted: {job_id}")
    else:
        _fail("Pass a job_id or --all.")


@app.command()
def rank(job_id: str = typer.Argument(None), all_jobs: bool = typer.Option(False, "--all")) -> None:
    """3 Estimate interview probability (one or --all)."""
    orch = _orch()
    if all_jobs:
        typer.echo(f"Batch: {orch.rank_all()}")
        return
    if not job_id:
        _fail("Pass a job_id or --all.")
    orch.rank(job_id)
    fit = orch.crm.get_fit(job_id)
    typer.echo(f"score={fit.score} p={fit.interview_probability:.2f} "
               f"recommended={fit.recommended}\n{fit.rationale}")


@app.command()
def select(job_id: str) -> None:
    """Gate A — mark a job as selected."""
    _orch().select(job_id)
    typer.echo(f"Selected: {job_id}")


@app.command()
def tailor(job_id: str) -> None:
    """4 Tailor the resume (with anti-fabrication guard)."""
    _orch().tailor(job_id)
    typer.echo(f"Tailored: {job_id} (review with `review-diff`).")


@app.command(name="review-diff")
def review_diff(job_id: str) -> None:
    """Gate D — show what changed and any flagged claims."""
    resume = _crm().get_tailored(job_id)
    if resume is None:
        _fail("Tailored resume not found.")
    typer.echo(f"== {resume.headline} ==")
    for note in resume.diff_notes:
        typer.echo(f"  • {note}")
    if resume.flagged_unsupported:
        typer.echo("\nUNSUPPORTED CLAIMS (fix before continuing):")
        for c in resume.flagged_unsupported:
            typer.echo(f"  ✗ {c}")
    else:
        typer.echo("\n✓ No unsupported claims.")


@app.command()
def document(job_id: str) -> None:
    """5 Render the ATS-safe PDF and validate it."""
    typer.echo(f"PDF: {_orch().document(job_id)}")


@app.command()
def assemble(job_id: str, cover_letter: bool = typer.Option(False, "--cover-letter")) -> None:
    """6 Build the application package (pending_approval)."""
    _orch().assemble(job_id, with_cover_letter=cover_letter)
    typer.echo(f"Package ready: {job_id}. Review with `review`, approve with `approve`.")


@app.command()
def run(job_id: str = typer.Argument(None), all_leads: bool = typer.Option(False, "--all")) -> None:
    """Run 2->6 and STOP at Gate B (never submits)."""
    orch = _orch()
    if all_leads:
        typer.echo(f"Batch: {orch.run_all()}")
        return
    if not job_id:
        _fail("Pass a job_id or --all.")
    status = orch.run_until_approval(job_id)
    typer.echo(f"Pipeline stopped at: {status.value}")


@app.command()
def autopilot(query: str = typer.Option(None), max_n: int = typer.Option(None, "--max")) -> None:
    """Discover + PREPARE high-fit applications up to Gate B (does not submit)."""
    r = _orch().autopilot(query, max_n)
    typer.echo(f"Prepared ({len(r['prepared'])}): {', '.join(r['prepared']) or '—'}")
    typer.echo(f"Skipped by policy/errors: {len(r['skipped'])}")
    if r["stopped"]:
        typer.echo(f"Stopped by: {r['stopped']}")


@app.command()
def review(job_id: str) -> None:
    """Gate B — full preview of what will be sent."""
    crm = _crm()
    job, draft = crm.get_job(job_id), crm.get_draft(job_id)
    if job is None or draft is None:
        _fail("No draft to review.")
    typer.echo(f"JOB: {job.title} @ {job.company}\nSEND: {job.apply_mode.value} -> "
               f"{job.apply_target or '—'}\nPDF: {draft.resume_pdf_path}\nCHECKLIST:")
    for item in draft.checklist:
        typer.echo(f"  - {item}")
    for qa in draft.screening:
        typer.echo(f"  Q: {qa.question}\n  A: {qa.answer}{'' if qa.grounded else '  (unsupported)'}")
    if draft.cover_letter:
        typer.echo(f"\nCOVER LETTER:\n{draft.cover_letter}")
    if draft.blocking_issues:
        typer.echo("\nBLOCKING ISSUES:")
        for b in draft.blocking_issues:
            typer.echo(f"  - {b}")
    else:
        typer.echo("\n✓ Ready for approval.")


@app.command()
def approve(job_id: str) -> None:
    """Gate B — explicit human approval."""
    _orch().approve(job_id)
    typer.echo(f"Approved: {job_id}. Now `submit {job_id}`.")


@app.command(name="approve-all")
def approve_all(yes: bool = typer.Option(False, "--yes", help="Confirm batch approval.")) -> None:
    """Gate B batch — approve every pending draft WITHOUT blocking issues."""
    crm = _crm()
    pending = [crm.get_draft(lead.id) for lead, _ in crm.list_leads(JobStatus.PENDING_APPROVAL)]
    ok = [d for d in pending if d and not d.blocking_issues]
    typer.echo(f"Approvable: {len(ok)} | Blocked: {len(pending) - len(ok)}")
    if not yes:
        typer.echo("Review with `report`, then re-run with --yes.")
        return
    typer.echo(f"Approved: {', '.join(_orch().approve_all()) or '—'}")


@app.command()
def reject(job_id: str) -> None:
    """Gate B — reject the application."""
    _orch().reject(job_id)
    typer.echo(f"Rejected: {job_id}")


@app.command()
def submit(job_id: str, consent: bool = typer.Option(False, "--consent", help="Gate C consent.")) -> None:
    """7 Submit an APPROVED application."""
    result = _orch().submit(job_id, consent=consent)
    typer.echo(f"✓ {result.confirmation}" if result.success else f"✗ {result.error}")


@app.command()
def feedback(job_id: str, outcome: str = typer.Argument(..., help="|".join(sorted(OUTCOMES)))) -> None:
    """Record a real outcome (feeds funnel learning)."""
    if outcome not in OUTCOMES:
        _fail(f"Invalid outcome. Use one of: {', '.join(sorted(OUTCOMES))}")
    _orch().record_outcome(job_id, outcome)
    typer.echo(f"Recorded: {job_id} -> {outcome}")


@app.command()
def rates() -> None:
    """Show learned callback rates."""
    data = learning.callback_rates(_crm())
    if not data:
        typer.echo("No history yet. Use `feedback` once you get replies.")
    for key, agg in sorted(data.items()):
        typer.echo(f"  {key:24} applied={int(agg['applied']):<3} rate={agg['rate']:.0%}")


@app.command()
def stop() -> None:
    """Kill-switch ON (creates data/STOP)."""
    s = get_settings()
    s.ensure_dirs()
    s.stop_file.write_text("stop\n", encoding="utf-8")
    typer.echo(f"Kill-switch ON ({s.stop_file}). Use `resume` to release.")


@app.command()
def resume() -> None:
    """Kill-switch OFF."""
    get_settings().stop_file.unlink(missing_ok=True)
    typer.echo("Kill-switch released.")


@app.command()
def report() -> None:
    """Dashboard: funnel, cost per step, learned rates, items needing attention."""
    crm, s = _crm(), get_settings()
    typer.echo("FUNNEL:")
    for st, n in sorted(crm.funnel().items()):
        typer.echo(f"  {st:16} {n}")
    typer.echo("\nCOST PER STEP:")
    for action, agg in crm.cost_by_action().items():
        typer.echo(f"  {action:20} calls={int(agg['count']):<4} ${agg['cost']:.4f}")
    typer.echo(f"  {'TOTAL':20} ${crm.total_cost():.4f}")
    typer.echo(f"\nKILL-SWITCH: {'ON' if policy.is_killed(s) else 'off'}")
    for key, agg in sorted(learning.callback_rates(crm).items()):
        typer.echo(f"  rate {key:24} {agg['rate']:.0%} (n={int(agg['applied'])})")
    attention = crm.needs_attention()
    typer.echo("\nNEEDS ATTENTION:" if attention else "\n✓ Nothing needs attention.")
    for status_name, ids in attention.items():
        typer.echo(f"  {status_name}: {', '.join(ids)}")


if __name__ == "__main__":
    app()
