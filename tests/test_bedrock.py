from app.bedrock import BedrockCommercialReviewer


class FakeBedrockClient:
    def converse(self, **kwargs):
        assert kwargs["modelId"] == "amazon.nova-2-lite-v1:0"
        return {
            "output": {"message": {"content": [{"text": "The invoice is above the approved baseline; hold payment pending justification."}]}},
            "usage": {"inputTokens": 42, "outputTokens": 14, "totalTokens": 56},
            "ResponseMetadata": {"RequestId": "req-test-123"},
        }


class BrokenBedrockClient:
    def converse(self, **kwargs):
        raise RuntimeError("simulated Bedrock outage")


def configured_reviewer():
    reviewer = BedrockCommercialReviewer()
    reviewer.enabled = True
    reviewer.model_id = "amazon.nova-2-lite-v1:0"
    return reviewer


def test_bedrock_success_records_evidence(monkeypatch):
    reviewer = configured_reviewer()
    monkeypatch.setattr(reviewer, "_client", lambda: FakeBedrockClient())

    result = reviewer.explain(
        {"decision": "HOLD_FOR_APPROVAL", "variance": 40.0},
        "fallback text",
    )

    assert result.source == "bedrock"
    assert result.model_id == "amazon.nova-2-lite-v1:0"
    assert result.request_id == "req-test-123"
    assert result.usage["totalTokens"] == 56
    assert "hold payment" in result.text.lower()
    assert result.error is None


def test_bedrock_failure_falls_back_without_changing_control(monkeypatch):
    reviewer = configured_reviewer()
    monkeypatch.setattr(reviewer, "_client", lambda: BrokenBedrockClient())

    result = reviewer.explain(
        {"decision": "HOLD_FOR_APPROVAL", "variance": 40.0},
        "Deterministic hold remains authoritative.",
    )

    assert result.source == "fallback"
    assert result.text == "Deterministic hold remains authoritative."
    assert "simulated Bedrock outage" in (result.error or "")


def test_bedrock_explicit_connection_test(monkeypatch):
    reviewer = configured_reviewer()
    monkeypatch.setattr(reviewer, "_client", lambda: FakeBedrockClient())

    result = reviewer.test_connection()

    assert result["success"] is True
    assert result["source"] == "bedrock"
    assert result["request_id"] == "req-test-123"
