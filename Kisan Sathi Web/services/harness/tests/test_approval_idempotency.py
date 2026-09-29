from __future__ import annotations

import asyncio

import pytest

from app.approvals import ApprovalError, ApprovalManager, request_digest
from app.audit import AuditLog
from app.orchestrator import Orchestrator
from app.providers.fake import FakeProvider, ProviderToolCall
from kisansathi_auth.claims import ActorScope


def test_approval_state_is_actor_and_payload_bound() -> None:
    actor = ActorScope("user-a", "tenant-a", "farmer-a", ("farmer",), "session-a")
    other = ActorScope("user-b", "tenant-b", "farmer-b", ("farmer",), "session-b")
    manager = ApprovalManager()
    value = manager.propose(request_id="approval-a", actor=actor, tool="create_field", arguments={"name": "North"}, now=100)
    assert value.status == "awaiting_confirmation"
    with pytest.raises(ApprovalError):
        manager.resolve(request_id="approval-a", actor=other, accepted=True, payload_hash=value.payload_hash, now=101)
    with pytest.raises(ApprovalError):
        manager.resolve(request_id="approval-a", actor=actor, accepted=True, payload_hash=request_digest("create_field", {"name": "South"}), now=101)
    assert manager.resolve(request_id="approval-a", actor=actor, accepted=True, payload_hash=value.payload_hash, now=101).status == "accepted"
    assert manager.resolve(request_id="approval-a", actor=actor, accepted=True, payload_hash=value.payload_hash, now=102).status == "accepted"


class RecordingExecutor:
    def __init__(self) -> None:
        self.calls = []

    async def execute(self, tool, arguments, actor, **kwargs):
        self.calls.append((tool, arguments, actor.farmer_id))
        return {"status": "ok", "summary": "saved", "data": {"id": "field-1"}, "request_id": kwargs["request_id"], "action": {"method": "POST", "path": "/v1/fields"}}


def test_duplicate_acceptance_has_one_authoritative_effect_and_audit_is_redacted() -> None:
    actor = ActorScope("user-a", "tenant-a", "farmer-a", ("farmer",), "session-a")
    executor = RecordingExecutor()
    provider = FakeProvider([ProviderToolCall("create_field", {"name": "North", "note": "secret"}, "call-a")])
    harness = Orchestrator(provider, tool_executor=executor, audit=AuditLog())
    harness.start_session(actor)
    pending = asyncio.run(harness.send_turn(actor, "session-a", "turn-a", [{"role": "user", "content": "create"}], workflow="record_update"))
    assert pending.status == "awaiting_confirmation"
    approval = harness.approvals.get(pending.approval_id, actor)
    first = asyncio.run(harness.resolve_approval(actor, "session-a", pending.approval_id, accepted=True, payload_hash=approval.payload_hash, workflow="record_update"))
    second = asyncio.run(harness.resolve_approval(actor, "session-a", pending.approval_id, accepted=True, payload_hash=approval.payload_hash, workflow="record_update"))
    assert first.status == second.status == "succeeded"
    assert len(executor.calls) == 1
    rendered = str(harness.audit.records)
    assert "secret" not in rendered
