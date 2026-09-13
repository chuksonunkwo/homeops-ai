from pathlib import Path

import pytest

from app.engine import HomeOpsEngine
from app.store import Store


@pytest.fixture()
def engine(tmp_path: Path) -> HomeOpsEngine:
    return HomeOpsEngine(Store(tmp_path / "test.db"))


def test_golden_hvac_flow_flags_invoice_variance(engine: HomeOpsEngine):
    job = engine.create_service_request("My AC isn't cooling. Handle it.")
    assert job["category"] == "hvac"

    comparison = engine.compare_quotes(job["id"])
    assert comparison["recommended_provider"] == "KlimaPro"
    assert len(comparison["quotes"]) == 3

    award = engine.approve_provider(job["id"], "KlimaPro")
    assert award["quote"]["amount"] == 95.0

    scheduled = engine.schedule_service(job["id"])
    assert scheduled["status"] == "SCHEDULED"
    assert "Tomorrow" in scheduled["appointment_window"]

    completed = engine.record_service_completion(job["id"])
    assert completed["status"] == "COMPLETED"

    review = engine.submit_invoice(
        job["id"],
        135,
        callout=45,
        service=50,
        materials=40,
        notes="Refrigerant added",
    )
    assert review["variance"] == 40.0
    assert review["variance_percentage"] == 42.1
    assert review["decision"] == "HOLD_FOR_APPROVAL"
    assert review["recommended_action"] == "REQUEST_JUSTIFICATION"


def test_invoice_at_or_below_quote_can_proceed(engine: HomeOpsEngine):
    job = engine.create_service_request("My AC needs a service")
    engine.request_quotes(job["id"])
    engine.approve_provider(job["id"], "KlimaPro")
    engine.schedule_service(job["id"])
    engine.record_service_completion(job["id"])
    review = engine.submit_invoice(job["id"], 90)
    assert review["decision"] == "APPROVE"
    assert review["variance"] == -5.0


def test_line_item_mismatch_is_rejected(engine: HomeOpsEngine):
    job = engine.create_service_request("AC is not cooling")
    engine.request_quotes(job["id"])
    engine.approve_provider(job["id"], "KlimaPro")
    with pytest.raises(ValueError, match="do not add up"):
        engine.submit_invoice(job["id"], 135, callout=45, service=40, materials=40)


def test_emergency_language_routes_away_from_normal_sourcing(engine: HomeOpsEngine):
    job = engine.create_service_request("There is smoke from the air conditioner")
    diag = engine.diagnose_service_request(job["id"])
    assert diag["emergency"] is True
    assert diag["recommended_path"] == "EMERGENCY_ESCALATION"


def test_existing_database_gets_bedrock_evidence_columns(tmp_path: Path):
    import sqlite3

    db_path = tmp_path / "legacy.db"
    con = sqlite3.connect(db_path)
    con.execute(
        """
        CREATE TABLE invoices (
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
            created_at TEXT NOT NULL
        )
        """
    )
    con.commit()
    con.close()

    Store(db_path)

    con = sqlite3.connect(db_path)
    columns = {row[1] for row in con.execute("PRAGMA table_info(invoices)")}
    con.close()
    assert {
        "ai_source",
        "ai_model_id",
        "ai_request_id",
        "ai_latency_ms",
        "ai_usage_json",
        "ai_error",
    }.issubset(columns)
