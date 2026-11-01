"""CRM repository: CRUD, dedup, status, audit, outcomes and funnel."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from ..models import (
    ApplicationDraft,
    AuditEntry,
    FitAssessment,
    JobLead,
    JobStatus,
    StructuredJob,
    SubmissionResult,
    TailoredResume,
)
from .db import get_connection, init_db


class CRM:
    def __init__(self, db_path: str | Path) -> None:
        self.conn = get_connection(db_path)
        init_db(self.conn)

    def close(self) -> None:
        self.conn.close()

    # -- leads -------------------------------------------------------------
    def lead_exists(self, url_canonical: str, content_hash: str | None = None) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM leads WHERE url_canonical = ? "
            "OR (content_hash IS NOT NULL AND content_hash = ?) LIMIT 1",
            (url_canonical, content_hash),
        )
        return cur.fetchone() is not None

    def add_lead(self, lead: JobLead, url_canonical: str) -> bool:
        if self.lead_exists(url_canonical, lead.content_hash):
            return False
        self.conn.execute(
            "INSERT INTO leads(id, source, url, url_canonical, content_hash, title, company, "
            "discovered_at, raw_snippet, status, data) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (lead.id, lead.source, lead.url, url_canonical, lead.content_hash, lead.title,
             lead.company, lead.discovered_at.isoformat(), lead.raw_snippet,
             JobStatus.DISCOVERED.value, lead.model_dump_json()),
        )
        self.conn.commit()
        return True

    def get_lead(self, job_id: str) -> JobLead | None:
        row = self.conn.execute("SELECT data FROM leads WHERE id = ?", (job_id,)).fetchone()
        return JobLead.model_validate_json(row["data"]) if row else None

    def set_status(self, job_id: str, status: JobStatus) -> None:
        self.conn.execute("UPDATE leads SET status = ? WHERE id = ?", (status.value, job_id))
        self.conn.commit()

    def get_status(self, job_id: str) -> JobStatus | None:
        row = self.conn.execute("SELECT status FROM leads WHERE id = ?", (job_id,)).fetchone()
        return JobStatus(row["status"]) if row else None

    def list_leads(self, status: JobStatus | None = None) -> list[tuple[JobLead, JobStatus]]:
        if status is None:
            rows = self.conn.execute("SELECT data, status FROM leads ORDER BY discovered_at").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT data, status FROM leads WHERE status = ? ORDER BY discovered_at",
                (status.value,)).fetchall()
        return [(JobLead.model_validate_json(r["data"]), JobStatus(r["status"])) for r in rows]

    # -- artifacts ---------------------------------------------------------
    def _upsert(self, table: str, job_id: str, payload: str) -> None:
        self.conn.execute(
            f"INSERT INTO {table}(job_id, data) VALUES (?, ?) "
            f"ON CONFLICT(job_id) DO UPDATE SET data = excluded.data", (job_id, payload))
        self.conn.commit()

    def _get(self, table: str, job_id: str):
        return self.conn.execute(f"SELECT data FROM {table} WHERE job_id = ?", (job_id,)).fetchone()

    def save_job(self, job: StructuredJob) -> None:
        self.conn.execute(
            "INSERT INTO jobs(job_id, data, updated_at) VALUES (?,?,?) ON CONFLICT(job_id) "
            "DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at",
            (job.lead_id, job.model_dump_json(), job.extracted_at.isoformat()))
        self.conn.commit()

    def get_job(self, job_id: str) -> StructuredJob | None:
        row = self._get("jobs", job_id)
        return StructuredJob.model_validate_json(row["data"]) if row else None

    def save_fit(self, fit: FitAssessment) -> None:
        self._upsert("fit", fit.job_id, fit.model_dump_json())

    def get_fit(self, job_id: str) -> FitAssessment | None:
        row = self._get("fit", job_id)
        return FitAssessment.model_validate_json(row["data"]) if row else None

    def save_tailored(self, resume: TailoredResume) -> None:
        self._upsert("tailored", resume.job_id, resume.model_dump_json())

    def get_tailored(self, job_id: str) -> TailoredResume | None:
        row = self._get("tailored", job_id)
        return TailoredResume.model_validate_json(row["data"]) if row else None

    def save_draft(self, draft: ApplicationDraft) -> None:
        self._upsert("drafts", draft.job_id, draft.model_dump_json())

    def get_draft(self, job_id: str) -> ApplicationDraft | None:
        row = self._get("drafts", job_id)
        return ApplicationDraft.model_validate_json(row["data"]) if row else None

    def save_submission(self, result: SubmissionResult) -> None:
        self.conn.execute("INSERT INTO submissions(id, job_id, data) VALUES (?,?,?)",
                          (uuid.uuid4().hex[:12], result.job_id, result.model_dump_json()))
        self.conn.commit()

    def _successful_submissions(self) -> list[SubmissionResult]:
        rows = self.conn.execute("SELECT data FROM submissions").fetchall()
        subs = [SubmissionResult.model_validate_json(r["data"]) for r in rows]
        return [s for s in subs if s.success]

    def submissions_today(self) -> int:
        today = date.today()
        return sum(1 for s in self._successful_submissions() if s.submitted_at.date() == today)

    def submissions_for_company(self, company: str) -> int:
        n = 0
        for s in self._successful_submissions():
            job = self.get_job(s.job_id)
            if job and job.company.lower() == company.lower():
                n += 1
        return n

    # -- outcomes ----------------------------------------------------------
    def record_outcome(self, job_id: str, outcome: str) -> None:
        self.conn.execute("INSERT INTO outcomes(id, job_id, outcome, ts) VALUES (?,?,?,?)",
                          (uuid.uuid4().hex[:12], job_id, outcome,
                           datetime.now(timezone.utc).isoformat()))
        self.conn.commit()

    def list_outcomes(self) -> list[tuple[str, str]]:
        rows = self.conn.execute("SELECT job_id, outcome FROM outcomes").fetchall()
        return [(r["job_id"], r["outcome"]) for r in rows]

    # -- audit / reports ---------------------------------------------------
    def audit(self, entry: AuditEntry) -> None:
        self.conn.execute(
            "INSERT INTO audit(id, ts, action, job_id, model, cost_usd, input_summary, "
            "output_summary) VALUES (?,?,?,?,?,?,?,?)",
            (entry.id, entry.ts.isoformat(), entry.action, entry.job_id, entry.model,
             entry.cost_usd, entry.input_summary, entry.output_summary))
        self.conn.commit()

    def total_cost(self) -> float:
        row = self.conn.execute("SELECT COALESCE(SUM(cost_usd), 0) AS c FROM audit").fetchone()
        return float(row["c"])

    def cost_by_action(self) -> dict[str, dict[str, float]]:
        rows = self.conn.execute(
            "SELECT action, COUNT(*) AS n, COALESCE(SUM(cost_usd), 0) AS c "
            "FROM audit GROUP BY action ORDER BY c DESC").fetchall()
        return {r["action"]: {"count": r["n"], "cost": float(r["c"])} for r in rows}

    def needs_attention(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for st in (JobStatus.PENDING_APPROVAL, JobStatus.NEEDS_MANUAL, JobStatus.FAILED):
            ids = [lead.id for lead, _ in self.list_leads(st)]
            if ids:
                out[st.value] = ids
        return out

    def funnel(self) -> dict[str, int]:
        rows = self.conn.execute("SELECT status, COUNT(*) AS n FROM leads GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}
