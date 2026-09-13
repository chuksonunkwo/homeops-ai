from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from .bedrock import BedrockCommercialReviewer
from .models import JobStatus, Provider
from .store import Store, utc_now


PROVIDERS: list[Provider] = [
    Provider(
        id="klimapro",
        name="KlimaPro",
        category="hvac",
        rating=4.8,
        base_price=95.0,
        arrival_window="Tomorrow, 9:00-11:00 AM",
        speed_score=0.82,
    ),
    Provider(
        id="coolair",
        name="CoolAir",
        category="hvac",
        rating=4.7,
        base_price=120.0,
        arrival_window="Today, 5:00-7:00 PM",
        speed_score=1.0,
    ),
    Provider(
        id="hometech",
        name="HomeTech",
        category="hvac",
        rating=4.5,
        base_price=105.0,
        arrival_window="Tomorrow, 1:00-3:00 PM",
        speed_score=0.72,
    ),
    Provider(
        id="aquacare",
        name="AquaCare",
        category="plumbing",
        rating=4.8,
        base_price=92.0,
        arrival_window="Today, 4:00-6:00 PM",
        speed_score=1.0,
    ),
    Provider(
        id="rapidfix",
        name="RapidFix",
        category="plumbing",
        rating=4.6,
        base_price=80.0,
        arrival_window="Tomorrow, 8:00-10:00 AM",
        speed_score=0.8,
    ),
    Provider(
        id="homepro",
        name="HomePro",
        category="plumbing",
        rating=4.7,
        base_price=75.0,
        arrival_window="Tomorrow, 12:00-2:00 PM",
        speed_score=0.7,
    ),
]


class HomeOpsEngine:
    def __init__(self, store: Store):
        self.store = store
        self.reviewer = BedrockCommercialReviewer()

    @staticmethod
    def classify_issue(issue: str) -> str:
        t = issue.lower()
        if any(x in t for x in ("ac", "air conditioner", "air conditioning", "cooling", "hvac")):
            return "hvac"
        if any(x in t for x in ("pipe", "leak", "plumb", "toilet", "tap", "faucet")):
            return "plumbing"
        return "general"

    @staticmethod
    def _job_id(category: str) -> str:
        prefix = "HVAC" if category == "hvac" else "PLB" if category == "plumbing" else "HOM"
        return f"{prefix}-{datetime.now(UTC).year}-{uuid.uuid4().hex[:5].upper()}"

    def create_service_request(
        self,
        issue: str,
        category: str = "auto",
        location: str = "Home",
        max_budget: float | None = None,
    ) -> dict[str, Any]:
        if not issue or len(issue.strip()) < 3:
            raise ValueError("Issue description must contain at least 3 characters.")
        resolved = self.classify_issue(issue) if category in ("", "auto") else category.lower()
        job_id = self._job_id(resolved)
        now = utc_now()
        job = {
            "id": job_id,
            "category": resolved,
            "issue": issue.strip(),
            "location": location.strip() or "Home",
            "status": JobStatus.OPEN.value,
            "max_budget": max_budget,
            "selected_provider_id": None,
            "selected_quote_id": None,
            "approved_amount": None,
            "appointment_window": None,
            "created_at": now,
            "updated_at": now,
        }
        self.store.add_job(job)
        self.store.log_event("SERVICE_REQUEST_CREATED", {"issue": issue, "category": resolved}, job_id)
        return job

    def get_job(self, job_id: str) -> dict[str, Any]:
        job = self.store.get_job(job_id)
        if not job:
            raise KeyError(f"Unknown job: {job_id}")
        job["quotes"] = self.store.list_quotes(job_id)
        invoice = self.store.latest_invoice(job_id)
        if invoice:
            job["latest_invoice"] = invoice
        job["events"] = self.store.list_events(job_id)
        return job

    def diagnose_service_request(self, job_id: str) -> dict[str, Any]:
        job = self.get_job(job_id)
        issue = job["issue"].lower()
        emergency = any(x in issue for x in ("flood", "smoke", "fire", "sparking", "gas smell"))
        diagnosis = {
            "job_id": job_id,
            "category": job["category"],
            "emergency": emergency,
            "recommended_path": "EMERGENCY_ESCALATION" if emergency else "SOURCE_SERVICE_PROVIDER",
            "safety_note": (
                "This could be dangerous. HomeOps has stopped the normal repair workflow. Move to a safe place and contact local emergency or safety services if there is immediate danger."
                if emergency
                else "No immediate safety warning was detected from the description."
            ),
        }
        self.store.log_event("REQUEST_DIAGNOSED", diagnosis, job_id)
        return diagnosis

    def search_providers(self, job_id: str) -> list[dict[str, Any]]:
        job = self.get_job(job_id)
        matches = [p for p in PROVIDERS if p.category == job["category"]]
        if not matches:
            matches = [
                Provider(
                    id="generalpro",
                    name="GeneralPro",
                    category="general",
                    rating=4.6,
                    base_price=100.0,
                    arrival_window="Tomorrow, 10:00 AM-12:00 PM",
                    speed_score=0.8,
                )
            ]
        result = [p.model_dump() for p in matches]
        self.store.log_event("PROVIDERS_SEARCHED", {"count": len(result)}, job_id)
        return result

    def request_quotes(self, job_id: str) -> list[dict[str, Any]]:
        job = self.get_job(job_id)
        existing = self.store.list_quotes(job_id)
        if existing:
            return existing
        providers = self.search_providers(job_id)
        self.store.update_job(job_id, status=JobStatus.QUOTING.value)
        scope = "Inspect, diagnose and restore normal operation; parts/materials beyond stated scope require approval."
        for p in providers:
            quote = {
                "id": f"Q-{uuid.uuid4().hex[:7].upper()}",
                "job_id": job_id,
                "provider_id": p["id"],
                "provider_name": p["name"],
                "amount": float(p["base_price"]),
                "arrival_window": p["arrival_window"],
                "rating": float(p["rating"]),
                "scope": scope,
                "score": None,
                "recommendation": None,
            }
            self.store.add_quote(quote)
        self.store.update_job(job_id, status=JobStatus.QUOTES_READY.value)
        quotes = self.store.list_quotes(job_id)
        self.store.log_event("QUOTES_RECEIVED", {"count": len(quotes)}, job_id)
        return quotes

    def compare_quotes(self, job_id: str) -> dict[str, Any]:
        quotes = self.store.list_quotes(job_id) or self.request_quotes(job_id)
        if not quotes:
            raise RuntimeError("No quotes available.")
        provider_by_id = {p.id: p for p in PROVIDERS}
        prices = [float(q["amount"]) for q in quotes]
        low, high = min(prices), max(prices)
        spread = max(high - low, 1.0)

        scored: list[dict[str, Any]] = []
        for q in quotes:
            p = provider_by_id.get(q["provider_id"])
            price_score = 1 - ((float(q["amount"]) - low) / spread)
            rating_score = max(0.0, min(float(q["rating"]) / 5.0, 1.0))
            speed_score = p.speed_score if p else 0.75
            total = round((price_score * 0.50 + rating_score * 0.30 + speed_score * 0.20) * 100, 1)
            q["score"] = total
            scored.append(q)

        scored.sort(key=lambda x: (-float(x["score"]), float(x["amount"])))
        best = scored[0]
        for i, q in enumerate(scored):
            recommendation = "BEST_VALUE" if i == 0 else "ALTERNATIVE"
            if q["provider_id"] == "coolair":
                recommendation = "FASTEST"
            q["recommendation"] = recommendation
            self.store.update_quote(q["id"], score=q["score"], recommendation=recommendation)

        result = {
            "job_id": job_id,
            "recommended_quote_id": best["id"],
            "recommended_provider": best["provider_name"],
            "basis": "50% price, 30% rating, 20% response speed",
            "quotes": scored,
        }
        self.store.log_event(
            "QUOTES_COMPARED",
            {"recommended_provider": best["provider_name"], "recommended_quote_id": best["id"]},
            job_id,
        )
        return result

    def approve_provider(self, job_id: str, provider_name_or_id: str) -> dict[str, Any]:
        quotes = self.store.list_quotes(job_id) or self.request_quotes(job_id)
        needle = provider_name_or_id.strip().lower()
        chosen = next(
            (
                q
                for q in quotes
                if q["provider_id"].lower() == needle or q["provider_name"].lower() == needle
            ),
            None,
        )
        if not chosen:
            raise ValueError(f"Provider '{provider_name_or_id}' does not have a quote for {job_id}.")
        job = self.store.update_job(
            job_id,
            status=JobStatus.AWARDED.value,
            selected_provider_id=chosen["provider_id"],
            selected_quote_id=chosen["id"],
            approved_amount=chosen["amount"],
        )
        self.store.log_event(
            "PROVIDER_APPROVED",
            {"provider": chosen["provider_name"], "approved_amount": chosen["amount"]},
            job_id,
        )
        return {"job": job, "quote": chosen}

    def schedule_service(self, job_id: str, appointment_window: str | None = None) -> dict[str, Any]:
        job = self.get_job(job_id)
        if not job.get("selected_quote_id"):
            raise ValueError("A provider must be approved before scheduling.")
        quote = self.store.get_quote(job["selected_quote_id"])
        if not quote:
            raise RuntimeError("Selected quote cannot be found.")
        window = appointment_window or quote["arrival_window"]
        job = self.store.update_job(
            job_id,
            status=JobStatus.SCHEDULED.value,
            appointment_window=window,
        )
        self.store.log_event("SERVICE_SCHEDULED", {"appointment_window": window}, job_id)
        return job

    def record_service_completion(self, job_id: str, completion_note: str = "Service completed") -> dict[str, Any]:
        job = self.get_job(job_id)
        if job["status"] not in {
            JobStatus.AWARDED.value,
            JobStatus.SCHEDULED.value,
            JobStatus.IN_PROGRESS.value,
        }:
            raise ValueError(f"Job cannot be completed from status {job['status']}.")
        job = self.store.update_job(job_id, status=JobStatus.COMPLETED.value)
        self.store.log_event("SERVICE_COMPLETED", {"note": completion_note}, job_id)
        return job

    def submit_invoice(
        self,
        job_id: str,
        total: float,
        callout: float = 0,
        service: float = 0,
        materials: float = 0,
        notes: str = "",
    ) -> dict[str, Any]:
        job = self.get_job(job_id)
        approved = job.get("approved_amount")
        if approved is None:
            raise ValueError("No approved quote exists for this job.")
        if total < 0:
            raise ValueError("Invoice total cannot be negative.")

        provided = round(callout + service + materials, 2)
        items: list[dict[str, Any]] = []
        if provided > 0:
            items = [
                {"description": "Call-out / inspection", "amount": round(callout, 2)},
                {"description": "Service labour", "amount": round(service, 2)},
                {"description": "Materials / parts", "amount": round(materials, 2)},
            ]
            items = [x for x in items if x["amount"] > 0]
            if abs(provided - total) > 0.01:
                raise ValueError("Invoice line items do not add up to the invoice total.")
        else:
            items = [{"description": notes or "Service invoice", "amount": round(total, 2)}]

        variance = round(total - float(approved), 2)
        pct = round((variance / float(approved) * 100), 1) if approved else 0.0
        if variance > 0:
            decision = "HOLD_FOR_APPROVAL"
            exception = "UNAPPROVED_ADDITIONAL_COST"
            action = "REQUEST_JUSTIFICATION"
            fallback = (
                f"Invoice is ${variance:.2f} ({pct:.1f}%) above the approved ${float(approved):.2f}. "
                "Hold payment until the additional cost is justified and approved."
            )
        else:
            decision = "APPROVE"
            exception = None
            action = "PROCESS_PAYMENT"
            fallback = (
                "Invoice does not exceed the approved quote. It can proceed to payment, subject to normal completion evidence."
            )

        payload = {
            "approved_amount": float(approved),
            "invoice_amount": float(total),
            "variance": variance,
            "variance_percentage": pct,
            "decision": decision,
            "line_items": items,
        }
        ai_review = self.reviewer.explain(payload, fallback)
        review = {
            "invoice_id": f"INV-{uuid.uuid4().hex[:7].upper()}",
            "job_id": job_id,
            "approved_amount": round(float(approved), 2),
            "invoice_amount": round(float(total), 2),
            "variance": variance,
            "variance_percentage": pct,
            "decision": decision,
            "exception": exception,
            "recommended_action": action,
            "rationale": ai_review.text,
            "line_items": items,
            "notes": notes,
            "ai_source": ai_review.source,
            "ai_model_id": ai_review.model_id,
            "ai_request_id": ai_review.request_id,
            "ai_latency_ms": ai_review.latency_ms,
            "ai_usage": ai_review.usage,
            "ai_error": ai_review.error,
        }
        self.store.add_invoice(review)
        self.store.update_job(job_id, status=JobStatus.INVOICE_REVIEW.value)
        self.store.log_event(
            "INVOICE_REVIEWED",
            {
                "invoice_id": review["invoice_id"],
                "decision": decision,
                "variance": variance,
                "ai_source": review["ai_source"],
                "ai_model_id": review["ai_model_id"],
                "ai_request_id": review["ai_request_id"],
            },
            job_id,
        )
        return review


    def challenge_invoice_variance(self, job_id: str, note: str = "Request supplier justification") -> dict[str, Any]:
        invoice = self.store.latest_invoice(job_id)
        if not invoice:
            raise ValueError("No invoice has been submitted.")
        if invoice["decision"] != "HOLD_FOR_APPROVAL":
            raise ValueError("The latest invoice is not on hold for a variance.")
        payload = {
            "invoice_id": invoice["id"],
            "variance": invoice["variance"],
            "variance_percentage": invoice["variance_percentage"],
            "status": "JUSTIFICATION_REQUESTED",
            "note": note.strip() or "Request supplier justification",
        }
        self.store.log_event("VARIANCE_CHALLENGED", payload, job_id)
        return payload

    @staticmethod
    def next_actions(job: dict[str, Any]) -> list[str]:
        status = job.get("status")
        if status == JobStatus.QUOTES_READY.value:
            return ["Choose the recommended provider", "Choose the cheapest", "Choose the fastest"]
        if status in {JobStatus.AWARDED.value, JobStatus.SCHEDULED.value, JobStatus.IN_PROGRESS.value}:
            return ["The technician completed the repair", "Reschedule to Friday 2-4 PM", "Show status"]
        if status == JobStatus.COMPLETED.value:
            return ["The final invoice is $135", "Show status"]
        if status == JobStatus.INVOICE_REVIEW.value:
            invoice = job.get("latest_invoice") or {}
            if invoice.get("decision") == "HOLD_FOR_APPROVAL":
                return ["Request justification", "Approve variance", "Why is it on hold?"]
            return ["Close job", "Show status"]
        if status == JobStatus.CLOSED.value:
            return ["Show status", "Reset"]
        return ["Show status"]

    def close_job(self, job_id: str, approve_variance: bool = False) -> dict[str, Any]:
        invoice = self.store.latest_invoice(job_id)
        if not invoice:
            raise ValueError("No invoice has been submitted.")
        if invoice["decision"] == "HOLD_FOR_APPROVAL" and not approve_variance:
            raise ValueError("Invoice variance must be explicitly approved before the job can be closed.")
        job = self.store.update_job(job_id, status=JobStatus.CLOSED.value)
        self.store.log_event("JOB_CLOSED", {"variance_override": approve_variance}, job_id)
        return job

    @staticmethod
    def extract_money(text: str) -> float | None:
        match = re.search(r"(?:\$|usd\s*)?(\d+(?:\.\d{1,2})?)", text.lower())
        return float(match.group(1)) if match else None
