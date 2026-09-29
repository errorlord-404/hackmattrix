from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/harness"))
sys.path.insert(0, str(ROOT / "packages/auth"))
sys.path.insert(0, str(ROOT / "packages/tool-registry"))


def test_provider_timeout_is_typed_and_never_successful():
    from app.orchestrator import Orchestrator
    from app.providers.fake import FakeProvider, ProviderFailure
    from kisansathi_auth.claims import ActorScope

    actor = ActorScope("user-a", "tenant-a", "farmer-a", ("farmer",), "session-a")
    harness = Orchestrator(FakeProvider([ProviderFailure("provider_timeout", retryable=True)]))
    session, _, _ = harness.start_session(actor)
    result = asyncio.run(harness.send_turn(actor, session.session_id, "turn-a", [{"role": "user", "content": "hello"}]))
    assert result.status == "degraded"
    assert any(event.payload.get("code") == "provider_timeout" for event in result.events)
