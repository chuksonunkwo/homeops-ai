from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from .config import (
    AWS_PROFILE,
    AWS_REGION,
    BEDROCK_ENABLED,
    BEDROCK_MAX_TOKENS,
    BEDROCK_MODEL_ID,
    BEDROCK_READ_TIMEOUT_SECONDS,
)


@dataclass(frozen=True)
class BedrockReviewResult:
    text: str
    source: str
    model_id: str | None = None
    request_id: str | None = None
    latency_ms: int | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BedrockCommercialReviewer:
    """Optional Amazon Bedrock explanation layer.

    The deterministic HomeOps commercial-control policy is authoritative.
    Bedrock receives only the already-calculated facts and may explain the
    decision; it is never allowed to approve or overturn an invoice variance.
    """

    def __init__(self) -> None:
        self.enabled = BEDROCK_ENABLED
        self.model_id = BEDROCK_MODEL_ID.strip()
        self.region = AWS_REGION
        self.profile = AWS_PROFILE.strip()

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.model_id)

    def _session(self):
        import boto3

        kwargs: dict[str, Any] = {"region_name": self.region}
        if self.profile:
            kwargs["profile_name"] = self.profile
        return boto3.Session(**kwargs)

    def _client(self):
        from botocore.config import Config

        session = self._session()
        return session.client(
            "bedrock-runtime",
            region_name=self.region,
            config=Config(
                connect_timeout=10,
                read_timeout=BEDROCK_READ_TIMEOUT_SECONDS,
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        try:
            from botocore.exceptions import ClientError

            if isinstance(exc, ClientError):
                error = exc.response.get("Error", {})
                code = str(error.get("Code", "ClientError"))
                message = str(error.get("Message", "AWS request failed"))
                return f"{code}: {message}"[:500]
        except Exception:
            pass
        return f"{exc.__class__.__name__}: {str(exc)}"[:500]

    def status(self) -> dict[str, Any]:
        # Configuration-only status: no network call and no credential discovery.
        # Live AWS validation is intentionally explicit via test_connection().
        return {
            "enabled": self.enabled,
            "configured": self.configured,
            "region": self.region,
            "model_id": self.model_id or None,
            "aws_profile": self.profile or None,
            "note": (
                "Configuration present. Run the explicit Bedrock test to verify AWS credentials and model access."
                if self.configured
                else "Set BEDROCK_ENABLED=true and BEDROCK_MODEL_ID, then provide AWS credentials through the standard AWS credential chain."
            ),
        }

    def _converse(self, *, system_text: str, user_text: str, max_tokens: int) -> BedrockReviewResult:
        started = time.perf_counter()
        client = self._client()
        response = client.converse(
            modelId=self.model_id,
            system=[{"text": system_text}],
            messages=[{"role": "user", "content": [{"text": user_text}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0},
        )
        latency_ms = round((time.perf_counter() - started) * 1000)
        content = response.get("output", {}).get("message", {}).get("content", [])
        text = next((str(item.get("text", "")).strip() for item in content if item.get("text")), "")
        metadata = response.get("ResponseMetadata", {})
        usage = response.get("usage", {}) or {}
        return BedrockReviewResult(
            text=text,
            source="bedrock",
            model_id=self.model_id,
            request_id=metadata.get("RequestId"),
            latency_ms=latency_ms,
            usage=usage,
            error=None,
        )

    def test_connection(self) -> dict[str, Any]:
        """Make one explicit, low-token Bedrock call for hackathon verification."""
        status = self.status()
        if not self.enabled:
            return {"success": False, **status, "error": "BEDROCK_ENABLED is false."}
        if not self.model_id:
            return {"success": False, **status, "error": "BEDROCK_MODEL_ID is empty."}

        try:
            result = self._converse(
                system_text="You are a connectivity test. Be concise.",
                user_text="Reply with exactly: BEDROCK_OK",
                max_tokens=20,
            )
            return {
                "success": True,
                **status,
                "response_text": result.text,
                "source": result.source,
                "request_id": result.request_id,
                "latency_ms": result.latency_ms,
                "usage": result.usage,
            }
        except Exception as exc:
            return {"success": False, **status, "error": self._safe_error(exc)}

    def explain(self, payload: dict[str, Any], fallback: str) -> BedrockReviewResult:
        if not self.configured:
            return BedrockReviewResult(text=fallback, source="fallback")

        try:
            result = self._converse(
                system_text=(
                    "You are HomeOps AI, a home-services commercial-control assistant. "
                    "The deterministic policy decision in the supplied JSON is final. "
                    "Never approve, reverse, or weaken that decision. Explain the decision in at most 55 words, "
                    "using only the supplied facts. Do not invent provider, invoice, or policy facts."
                ),
                user_text=json.dumps(payload, separators=(",", ":"), sort_keys=True),
                max_tokens=BEDROCK_MAX_TOKENS,
            )
            if not result.text:
                return BedrockReviewResult(
                    text=fallback,
                    source="fallback",
                    model_id=self.model_id,
                    request_id=result.request_id,
                    latency_ms=result.latency_ms,
                    usage=result.usage,
                    error="Bedrock returned no text content.",
                )
            return result
        except Exception as exc:
            # Bedrock is an enhancement, never a dependency for the core control.
            return BedrockReviewResult(
                text=fallback,
                source="fallback",
                model_id=self.model_id or None,
                error=self._safe_error(exc),
            )
