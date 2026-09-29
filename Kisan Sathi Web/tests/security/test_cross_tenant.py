from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/harness"))
sys.path.insert(0, str(ROOT / "packages/auth"))
sys.path.insert(0, str(ROOT / "packages/tool-registry"))


def test_actor_scope_is_immutable_and_rejects_unbounded_identity():
    from kisansathi_auth.claims import ActorScope, ClaimsValidationError

    actor = ActorScope("user-a", "tenant-a", "farmer-a", ("farmer",), "session-a")
    with pytest.raises((AttributeError, TypeError)):
        actor.farmer_id = "farmer-b"  # type: ignore[misc]
    with pytest.raises(ClaimsValidationError):
        ActorScope("user-a", "tenant/a", "farmer-a", ("farmer",), "session-a")
