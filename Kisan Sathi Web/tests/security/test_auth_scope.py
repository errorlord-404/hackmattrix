from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/harness"))
sys.path.insert(0, str(ROOT / "packages/auth"))
sys.path.insert(0, str(ROOT / "packages/tool-registry"))


def test_harness_session_cannot_be_used_by_another_actor():
    from app.orchestrator import Orchestrator, OrchestratorError
    from app.providers.fake import FakeProvider
    from kisansathi_auth.claims import ActorScope

    owner = ActorScope("user-a", "tenant-a", "farmer-a", ("farmer",), "session-a")
    other = ActorScope("user-b", "tenant-b", "farmer-b", ("farmer",), "session-b")
    harness = Orchestrator(FakeProvider())
    session, _, _ = harness.start_session(owner)
    with pytest.raises(OrchestratorError) as error:
        harness.require_session(other, session.session_id)
    assert error.value.code == "session_forbidden"
