from __future__ import annotations

import re
from typing import Any

from .engine import HomeOpsEngine
from .models import JobStatus


class HomeOpsConversation:
    """Deterministic conversation orchestrator for the Alexa+ simulation.

    It deliberately keeps commercial approvals and emergency routing outside an LLM.
    The same HomeOpsEngine methods are exposed as MCP tools in app.main.
    """

    SERVICE_HINTS = (
        "ac",
        "air conditioner",
        "air conditioning",
        "cooling",
        "hvac",
        "pipe",
        "leak",
        "plumb",
        "toilet",
        "tap",
        "faucet",
    )

    def __init__(self, engine: HomeOpsEngine):
        self.engine = engine

    @staticmethod
    def _response(
        reply: str,
        action: str,
        *,
        job_id: str | None = None,
        suggestions: list[str] | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "success": True,
            "reply": reply,
            "job_id": job_id,
            "action": action,
            "suggestions": suggestions or [],
        }
        payload.update(extra)
        return payload

    @staticmethod
    def extract_budget(text: str) -> float | None:
        patterns = (
            r"(?:budget|max(?:imum)?|under|below|less than|up to)\s*(?:is|of|:)?\s*(?:usd\s*)?\$?\s*(\d+(?:\.\d{1,2})?)",
            r"\$\s*(\d+(?:\.\d{1,2})?)\s*(?:budget|max|maximum)",
        )
        lower = text.lower()
        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                return float(match.group(1))
        return None

    @staticmethod
    def _appointment_from_message(text: str) -> str | None:
        lower = text.lower()
        for marker in ("reschedule to ", "schedule for ", "schedule to "):
            idx = lower.find(marker)
            if idx >= 0:
                value = text[idx + len(marker):].strip(" .")
                return value or None
        return None

    @staticmethod
    def _is_service_request(lower: str) -> bool:
        return any(token in lower for token in HomeOpsConversation.SERVICE_HINTS)

    def _choose_from_preference(self, job_id: str, lower: str) -> str | None:
        comparison = self.engine.compare_quotes(job_id)
        quotes = comparison["quotes"]
        if any(x in lower for x in ("best value", "recommended", "recommendation")):
            return comparison["recommended_provider"]
        if "cheapest" in lower or "lowest price" in lower:
            return min(quotes, key=lambda q: float(q["amount"]))["provider_name"]
        if any(x in lower for x in ("fastest", "soonest", "earliest")):
            fastest = next((q for q in quotes if q.get("recommendation") == "FASTEST"), None)
            return (fastest or quotes[0])["provider_name"]
        return None

    def handle(self, message: str, job_id: str | None = None) -> dict[str, Any]:
        message = message.strip()
        if not message:
            raise ValueError("message is required")
        lower = message.lower()

        if lower in {"reset", "start over", "restart demo"}:
            self.engine.store.reset()
            return self._response(
                "You're ready to start another repair. Tell me what needs fixing.",
                "RESET",
                suggestions=["My AC isn't cooling. Handle it.", "My kitchen pipe is leaking."],
            )

        if not job_id:
            if not self._is_service_request(lower):
                return self._response(
                    "Tell me what needs fixing at home. For this demo, I can help with AC and plumbing problems.",
                    "NEED_SERVICE_REQUEST",
                    suggestions=["My AC isn't cooling. Handle it.", "My kitchen pipe is leaking."],
                )

            budget = self.extract_budget(message)
            job = self.engine.create_service_request(message, max_budget=budget)
            diagnosis = self.engine.diagnose_service_request(job["id"])
            if diagnosis["emergency"]:
                return self._response(
                    diagnosis["safety_note"],
                    "EMERGENCY_ESCALATION",
                    job_id=job["id"],
                    suggestions=["Show status", "Reset"],
                    job=self.engine.get_job(job["id"]),
                    diagnosis=diagnosis,
                )

            comparison = self.engine.compare_quotes(job["id"])
            quotes = comparison["quotes"]
            cheapest = min(quotes, key=lambda q: float(q["amount"]))
            fastest = next((q for q in quotes if q.get("recommendation") == "FASTEST"), None)
            budget_line = ""
            if budget is not None:
                within = [q for q in quotes if float(q["amount"]) <= budget]
                budget_line = f" {len(within)} of {len(quotes)} quotes are within your ${budget:.2f} budget."
            reply = (
                f"I found {len(quotes)} suitable options. "
                f"{comparison['recommended_provider']} is my recommendation at "
                f"${next(q['amount'] for q in quotes if q['provider_name'] == comparison['recommended_provider']):.2f}. "
                f"The lowest price is {cheapest['provider_name']} at ${cheapest['amount']:.2f}."
                + (f" The soonest available option is {fastest['provider_name']}." if fastest else "")
                + budget_line
            )
            return self._response(
                reply,
                "QUOTES_READY",
                job_id=job["id"],
                suggestions=[
                    f"Choose {comparison['recommended_provider']}",
                    "Choose the cheapest",
                    "Choose the fastest",
                    "Show status",
                ],
                comparison=comparison,
                job=self.engine.get_job(job["id"]),
            )

        job_id = str(job_id)
        job = self.engine.get_job(job_id)
        provider_names = [q["provider_name"] for q in job.get("quotes", [])]

        if any(x in lower for x in ("approve variance", "approve the variance", "approve extra", "approve additional cost")):
            closed = self.engine.close_job(job_id, approve_variance=True)
            return self._response(
                "You approved the additional cost. The repair is now closed and the decision is recorded.",
                "VARIANCE_APPROVED_AND_CLOSED",
                job_id=job_id,
                suggestions=["Show status", "Reset"],
                job=self.engine.get_job(job_id),
                closed_job=closed,
            )

        if any(x in lower for x in ("challenge invoice", "challenge the invoice", "reject variance", "request justification", "ask for justification")):
            latest = job.get("latest_invoice")
            if not latest:
                raise ValueError("There is no invoice to challenge yet.")
            challenge = self.engine.challenge_invoice_variance(job_id, message)
            return self._response(
                "I've asked the provider to explain the additional charge. Payment remains on hold while you wait for a response.",
                "VARIANCE_CHALLENGED",
                job_id=job_id,
                suggestions=["Show status", "Approve variance", "Why is it on hold?"],
                job=self.engine.get_job(job_id),
                challenge=challenge,
            )

        if lower in {"close", "close job", "close the job"}:
            closed = self.engine.close_job(job_id)
            return self._response(
                "The repair is closed and the final decision is recorded.",
                "JOB_CLOSED",
                job_id=job_id,
                suggestions=["Show status", "Reset"],
                job=self.engine.get_job(job_id),
                closed_job=closed,
            )

        selected_name = next((name for name in provider_names if name.lower() in lower), None)
        preference_name = self._choose_from_preference(job_id, lower) if job.get("quotes") else None
        if selected_name or preference_name or lower.startswith("choose ") or lower.startswith("select "):
            candidate = selected_name or preference_name
            if candidate is None:
                parts = message.split(" ", 1)
                candidate = parts[1].strip() if len(parts) > 1 else ""
            approved = self.engine.approve_provider(job_id, candidate)
            scheduled = self.engine.schedule_service(job_id)
            provider = approved["quote"]["provider_name"]
            return self._response(
                f"{provider} is booked for {scheduled['appointment_window']} at an agreed price of "
                f"${approved['quote']['amount']:.2f}. I'll flag any later charge above that amount.",
                "PROVIDER_SCHEDULED",
                job_id=job_id,
                suggestions=["Show status", "The technician completed the repair", "Reschedule to Friday 2-4 PM"],
                job=self.engine.get_job(job_id),
            )

        if "reschedule" in lower or "schedule for" in lower or "schedule to" in lower:
            window = self._appointment_from_message(message)
            if not window:
                return self._response(
                    "Tell me the new appointment window, for example: Reschedule to Friday 2-4 PM.",
                    "NEED_APPOINTMENT_WINDOW",
                    job_id=job_id,
                    suggestions=["Reschedule to Friday 2-4 PM", "Show status"],
                    job=job,
                )
            scheduled = self.engine.schedule_service(job_id, window)
            return self._response(
                f"Your visit has been moved to {scheduled['appointment_window']}.",
                "SERVICE_RESCHEDULED",
                job_id=job_id,
                suggestions=["Show status", "The technician completed the repair"],
                job=self.engine.get_job(job_id),
            )

        if any(x in lower for x in ("completed", "finished", "job is done", "repair is done", "technician is done")):
            self.engine.record_service_completion(job_id, message)
            return self._response(
                f"The repair is marked complete. Send the final bill and I'll check it against the agreed ${float(job.get('approved_amount') or 0):.2f} price.",
                "COMPLETED",
                job_id=job_id,
                suggestions=["The final invoice is $135", "Show status"],
                job=self.engine.get_job(job_id),
            )

        invoice_context = "invoice" in lower or job["status"] in {JobStatus.COMPLETED.value, JobStatus.INVOICE_REVIEW.value}
        amount = self.engine.extract_money(message) if invoice_context else None
        if "invoice" in lower and amount is None:
            return self._response(
                "What is the invoice total?",
                "NEED_INVOICE_AMOUNT",
                job_id=job_id,
                suggestions=["The final invoice is $135", "Show status"],
                job=job,
            )
        if amount is not None:
            approved_amount = float(job.get("approved_amount") or 0)
            if round(amount, 2) == 135.00 and round(approved_amount, 2) == 95.00:
                review = self.engine.submit_invoice(
                    job_id,
                    135.00,
                    callout=45.00,
                    service=50.00,
                    materials=40.00,
                    notes="Technician added refrigerant during repair.",
                )
            else:
                review = self.engine.submit_invoice(job_id, amount, notes="Final service invoice")

            if review["decision"] == "HOLD_FOR_APPROVAL":
                reply = (
                    f"The final bill is ${review['variance']:.2f} ({review['variance_percentage']:.1f}%) higher than the agreed price. "
                    "I haven't approved the extra cost. I recommend asking the provider to explain it before payment."
                )
                suggestions = ["Request justification", "Approve variance", "Why is it on hold?", "Show status"]
            else:
                reply = "The invoice is within the approved commercial baseline and can proceed to payment controls."
                suggestions = ["Close job", "Show status"]
            if review.get("ai_source") == "bedrock":
                reply += f" Amazon Bedrock generated the explanation using {review.get('ai_model_id')}."
            return self._response(
                reply,
                "INVOICE_REVIEWED",
                job_id=job_id,
                suggestions=suggestions,
                invoice_review=review,
                job=self.engine.get_job(job_id),
            )

        if any(x in lower for x in ("why is it on hold", "why hold", "why was it held", "explain variance", "why")):
            latest = job.get("latest_invoice")
            if latest:
                return self._response(
                    latest["rationale"],
                    "INVOICE_EXPLAINED",
                    job_id=job_id,
                    suggestions=["Request justification", "Approve variance", "Show status"],
                    job=job,
                )

        if any(x in lower for x in ("status", "what's happening", "what is happening", "update", "progress")):
            current = self.engine.get_job(job_id)
            parts = [f"{job_id} is {current['status']}."]
            if current.get("approved_amount") is not None:
                parts.append(f"Approved amount: ${float(current['approved_amount']):.2f}.")
            if current.get("appointment_window"):
                parts.append(f"Appointment: {current['appointment_window']}.")
            if current.get("latest_invoice"):
                inv = current["latest_invoice"]
                parts.append(f"Latest invoice decision: {inv['decision']}.")
            return self._response(
                " ".join(parts),
                "STATUS",
                job_id=job_id,
                suggestions=self.engine.next_actions(current),
                job=current,
            )

        return self._response(
            "I can help you choose a provider, move the appointment, mark the work complete, review the final bill, explain an extra charge, or show the current status.",
            "HELP",
            job_id=job_id,
            suggestions=self.engine.next_actions(job),
            job=job,
        )
