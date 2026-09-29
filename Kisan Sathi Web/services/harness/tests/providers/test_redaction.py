from __future__ import annotations

from app.secrets import redact


def test_recursive_redaction_removes_sentinel_secrets() -> None:
    value = redact({"authorization": "Bearer sentinel", "nested": [{"api_key": "sentinel"}], "message": "authorization=sentinel"})
    rendered = str(value)
    assert "sentinel" not in rendered
    assert value["authorization"] == "[REDACTED]"
