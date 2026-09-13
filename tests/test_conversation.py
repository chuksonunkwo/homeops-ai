from pathlib import Path

import pytest

from app.conversation import HomeOpsConversation
from app.engine import HomeOpsEngine
from app.store import Store


@pytest.fixture()
def convo(tmp_path: Path) -> HomeOpsConversation:
    return HomeOpsConversation(HomeOpsEngine(Store(tmp_path / "conversation.db")))


def start_hvac(convo: HomeOpsConversation):
    return convo.handle("My AC isn't cooling. Handle it.")


def advance_to_invoice_hold(convo: HomeOpsConversation):
    first = start_hvac(convo)
    job_id = first["job_id"]
    convo.handle("Choose KlimaPro", job_id)
    convo.handle("The technician completed the repair", job_id)
    review = convo.handle("The final invoice is $135", job_id)
    return job_id, review


def test_budget_parser_handles_natural_phrases(convo: HomeOpsConversation):
    assert convo.extract_budget("Keep it under $90") == 90.0
    assert convo.extract_budget("My maximum budget is USD 125") == 125.0
    assert convo.extract_budget("No budget yet") is None


def test_hvac_request_returns_ranked_quotes_and_suggestions(convo: HomeOpsConversation):
    result = start_hvac(convo)
    assert result["action"] == "QUOTES_READY"
    assert result["comparison"]["recommended_provider"] == "KlimaPro"
    assert len(result["comparison"]["quotes"]) == 3
    assert "Choose KlimaPro" in result["suggestions"]


def test_plumbing_request_is_budget_aware(convo: HomeOpsConversation):
    result = convo.handle("My kitchen pipe is leaking. Keep it under $90.")
    assert result["action"] == "QUOTES_READY"
    assert result["comparison"]["recommended_provider"] == "HomePro"
    assert "2 of 3 quotes are within your $90.00 budget" in result["reply"]


def test_emergency_language_stops_normal_sourcing(convo: HomeOpsConversation):
    result = convo.handle("There is smoke coming from my air conditioner.")
    assert result["action"] == "EMERGENCY_ESCALATION"
    assert result["diagnosis"]["emergency"] is True
    assert result["job"]["quotes"] == []


def test_choose_cheapest_maps_to_correct_provider(convo: HomeOpsConversation):
    first = start_hvac(convo)
    result = convo.handle("Choose the cheapest", first["job_id"])
    assert result["action"] == "PROVIDER_SCHEDULED"
    assert result["job"]["selected_provider_id"] == "klimapro"
    assert result["job"]["approved_amount"] == 95.0


def test_choose_fastest_maps_to_correct_provider(convo: HomeOpsConversation):
    first = start_hvac(convo)
    result = convo.handle("Choose the fastest", first["job_id"])
    assert result["job"]["selected_provider_id"] == "coolair"
    assert result["job"]["approved_amount"] == 120.0


def test_reschedule_records_new_window(convo: HomeOpsConversation):
    first = start_hvac(convo)
    job_id = first["job_id"]
    convo.handle("Choose KlimaPro", job_id)
    result = convo.handle("Reschedule to Friday 2-4 PM", job_id)
    assert result["action"] == "SERVICE_RESCHEDULED"
    assert result["job"]["appointment_window"] == "Friday 2-4 PM"


def test_amount_only_is_treated_as_invoice_after_completion(convo: HomeOpsConversation):
    first = start_hvac(convo)
    job_id = first["job_id"]
    convo.handle("Choose KlimaPro", job_id)
    convo.handle("The technician completed the repair", job_id)
    result = convo.handle("$90", job_id)
    assert result["action"] == "INVOICE_REVIEWED"
    assert result["invoice_review"]["decision"] == "APPROVE"


def test_variance_challenge_keeps_hold_and_adds_audit_event(convo: HomeOpsConversation):
    job_id, _ = advance_to_invoice_hold(convo)
    result = convo.handle("Request justification", job_id)
    assert result["action"] == "VARIANCE_CHALLENGED"
    assert result["job"]["status"] == "INVOICE_REVIEW"
    assert result["job"]["latest_invoice"]["decision"] == "HOLD_FOR_APPROVAL"
    assert result["job"]["events"][-1]["event_type"] == "VARIANCE_CHALLENGED"


def test_variance_requires_explicit_approval_before_closure(convo: HomeOpsConversation):
    job_id, _ = advance_to_invoice_hold(convo)
    with pytest.raises(ValueError, match="explicitly approved"):
        convo.handle("Close job", job_id)

    result = convo.handle("Approve variance", job_id)
    assert result["action"] == "VARIANCE_APPROVED_AND_CLOSED"
    assert result["job"]["status"] == "CLOSED"
    assert result["job"]["events"][-1]["event_type"] == "JOB_CLOSED"
    assert result["job"]["events"][-1]["details"]["variance_override"] is True


def test_invoice_within_baseline_can_close_without_override(convo: HomeOpsConversation):
    first = start_hvac(convo)
    job_id = first["job_id"]
    convo.handle("Choose KlimaPro", job_id)
    convo.handle("Technician is done", job_id)
    invoice = convo.handle("Invoice is $90", job_id)
    assert invoice["invoice_review"]["decision"] == "APPROVE"
    closed = convo.handle("Close job", job_id)
    assert closed["job"]["status"] == "CLOSED"


def test_status_response_preserves_state(convo: HomeOpsConversation):
    first = start_hvac(convo)
    job_id = first["job_id"]
    convo.handle("Choose KlimaPro", job_id)
    result = convo.handle("What's happening?", job_id)
    assert result["action"] == "STATUS"
    assert "$95.00" in result["reply"]
    assert "Tomorrow" in result["reply"]
