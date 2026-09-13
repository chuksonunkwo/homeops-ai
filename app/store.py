from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    @staticmethod
    def _column_names(con: sqlite3.Connection, table: str) -> set[str]:
        rows = con.execute(f"PRAGMA table_info({table})").fetchall()
        return {str(row[1]) for row in rows}

    def _ensure_invoice_ai_columns(self, con: sqlite3.Connection) -> None:
        """Forward-compatible local migration for existing MVP databases."""
        columns = self._column_names(con, "invoices")
        additions = {
            "ai_source": "TEXT NOT NULL DEFAULT 'fallback'",
            "ai_model_id": "TEXT",
            "ai_request_id": "TEXT",
            "ai_latency_ms": "INTEGER",
            "ai_usage_json": "TEXT NOT NULL DEFAULT '{}'",
            "ai_error": "TEXT",
        }
        for name, definition in additions.items():
            if name not in columns:
                con.execute(f"ALTER TABLE invoices ADD COLUMN {name} {definition}")

    def init_schema(self) -> None:
        with self.connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    issue TEXT NOT NULL,
                    location TEXT NOT NULL,
                    status TEXT NOT NULL,
                    max_budget REAL,
                    selected_provider_id TEXT,
                    selected_quote_id TEXT,
                    approved_amount REAL,
                    appointment_window TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS quotes (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    provider_id TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    arrival_window TEXT NOT NULL,
                    rating REAL NOT NULL,
                    scope TEXT NOT NULL,
                    score REAL,
                    recommendation TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );

                CREATE TABLE IF NOT EXISTS invoices (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    approved_amount REAL NOT NULL,
                    invoice_amount REAL NOT NULL,
                    variance REAL NOT NULL,
                    variance_percentage REAL NOT NULL,
                    decision TEXT NOT NULL,
                    exception TEXT,
                    recommended_action TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    line_items_json TEXT NOT NULL,
                    ai_source TEXT NOT NULL DEFAULT 'fallback',
                    ai_model_id TEXT,
                    ai_request_id TEXT,
                    ai_latency_ms INTEGER,
                    ai_usage_json TEXT NOT NULL DEFAULT '{}',
                    ai_error TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    event_type TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            self._ensure_invoice_ai_columns(con)

    def reset(self) -> None:
        with self.connect() as con:
            con.executescript(
                """
                DELETE FROM events;
                DELETE FROM invoices;
                DELETE FROM quotes;
                DELETE FROM jobs;
                """
            )

    def add_job(self, job: dict[str, Any]) -> None:
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO jobs (
                    id, category, issue, location, status, max_budget,
                    selected_provider_id, selected_quote_id, approved_amount,
                    appointment_window, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job["id"], job["category"], job["issue"], job["location"],
                    job["status"], job.get("max_budget"), job.get("selected_provider_id"),
                    job.get("selected_quote_id"), job.get("approved_amount"),
                    job.get("appointment_window"), job["created_at"], job["updated_at"],
                ),
            )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as con:
            row = con.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

    def update_job(self, job_id: str, **fields: Any) -> dict[str, Any]:
        if not fields:
            job = self.get_job(job_id)
            if job is None:
                raise KeyError(job_id)
            return job
        fields["updated_at"] = utc_now()
        clauses = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [job_id]
        with self.connect() as con:
            cur = con.execute(f"UPDATE jobs SET {clauses} WHERE id = ?", values)
            if cur.rowcount != 1:
                raise KeyError(job_id)
        job = self.get_job(job_id)
        assert job is not None
        return job

    def add_quote(self, quote: dict[str, Any]) -> None:
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO quotes (
                    id, job_id, provider_id, provider_name, amount,
                    arrival_window, rating, scope, score, recommendation, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    quote["id"], quote["job_id"], quote["provider_id"],
                    quote["provider_name"], quote["amount"], quote["arrival_window"],
                    quote["rating"], quote["scope"], quote.get("score"),
                    quote.get("recommendation"), utc_now(),
                ),
            )

    def update_quote(self, quote_id: str, **fields: Any) -> None:
        if not fields:
            return
        clauses = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [quote_id]
        with self.connect() as con:
            con.execute(f"UPDATE quotes SET {clauses} WHERE id = ?", values)

    def get_quote(self, quote_id: str) -> dict[str, Any] | None:
        with self.connect() as con:
            row = con.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,)).fetchone()
        return dict(row) if row else None

    def list_quotes(self, job_id: str) -> list[dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute(
                "SELECT * FROM quotes WHERE job_id = ? ORDER BY amount ASC", (job_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def add_invoice(self, review: dict[str, Any]) -> None:
        line_items = review.get("line_items", [])
        ai_usage = review.get("ai_usage") or {}
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO invoices (
                    id, job_id, approved_amount, invoice_amount, variance,
                    variance_percentage, decision, exception, recommended_action,
                    rationale, line_items_json, ai_source, ai_model_id,
                    ai_request_id, ai_latency_ms, ai_usage_json, ai_error, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review["invoice_id"], review["job_id"], review["approved_amount"],
                    review["invoice_amount"], review["variance"],
                    review["variance_percentage"], review["decision"],
                    review.get("exception"), review["recommended_action"],
                    review["rationale"], json.dumps(line_items),
                    review.get("ai_source", "fallback"), review.get("ai_model_id"),
                    review.get("ai_request_id"), review.get("ai_latency_ms"),
                    json.dumps(ai_usage), review.get("ai_error"), utc_now(),
                ),
            )

    def latest_invoice(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as con:
            row = con.execute(
                "SELECT * FROM invoices WHERE job_id = ? ORDER BY created_at DESC LIMIT 1",
                (job_id,),
            ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["line_items"] = json.loads(data.pop("line_items_json"))
        usage_json = data.pop("ai_usage_json", "{}") or "{}"
        try:
            data["ai_usage"] = json.loads(usage_json)
        except json.JSONDecodeError:
            data["ai_usage"] = {}
        return data

    def log_event(self, event_type: str, details: dict[str, Any], job_id: str | None = None) -> None:
        with self.connect() as con:
            con.execute(
                "INSERT INTO events (job_id, event_type, details_json, created_at) VALUES (?, ?, ?, ?)",
                (job_id, event_type, json.dumps(details), utc_now()),
            )

    def list_events(self, job_id: str) -> list[dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute(
                "SELECT * FROM events WHERE job_id = ? ORDER BY id ASC", (job_id,)
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            data = dict(row)
            data["details"] = json.loads(data.pop("details_json"))
            out.append(data)
        return out
