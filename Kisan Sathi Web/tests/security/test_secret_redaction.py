from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/harness"))


def test_audit_redacts_credentials_recursively():
    from app.audit import redact

    value = redact({"api_key": "secret-value", "nested": [{"authorization": "Bearer token"}], "message": "safe"})
    assert value == {"api_key": "[REDACTED]", "nested": [{"authorization": "[REDACTED]"}], "message": "safe"}
