from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/harness"))
sys.path.insert(0, str(ROOT / "packages/auth"))


def test_event_envelope_has_frozen_cursor_and_identity_fields():
    from app.protocol import EventEnvelope

    event = EventEnvelope("session-1", "turn-1", 1, "ready", {"status": "ready"})
    payload = json.loads(event.ndjson())
    assert payload["version"] == "1.0"
    assert payload["event_id"] == "evt-session-1-1"
    assert payload["delivery"] == {"cursor": "1", "replay": False, "duplicate": False}
