from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    OPEN = "OPEN"
    QUOTING = "QUOTING"
    QUOTES_READY = "QUOTES_READY"
    AWARDED = "AWARDED"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    INVOICE_REVIEW = "INVOICE_REVIEW"
    CLOSED = "CLOSED"


class ServiceRequest(BaseModel):
    issue: str = Field(min_length=3, max_length=500)
    category: str = "auto"
    location: str = "Home"
    max_budget: float | None = Field(default=None, ge=0)


class Provider(BaseModel):
    id: str
    name: str
    category: str
    rating: float
    base_price: float
    arrival_window: str
    speed_score: float
    verified: bool = True


class Quote(BaseModel):
    id: str
    job_id: str
    provider_id: str
    provider_name: str
    amount: float
    arrival_window: str
    rating: float
    scope: str
    score: float | None = None
    recommendation: str | None = None


class InvoiceLineItem(BaseModel):
    description: str
    amount: float = Field(ge=0)


class InvoiceReview(BaseModel):
    invoice_id: str
    job_id: str
    approved_amount: float
    invoice_amount: float
    variance: float
    variance_percentage: float
    decision: str
    exception: str | None = None
    recommended_action: str
    rationale: str
    line_items: list[InvoiceLineItem]


class ToolResult(BaseModel):
    success: bool = True
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
