from __future__ import annotations

import asyncio
import pytest

from app.orchestrator import Orchestrator, OrchestratorError
from app.providers.fake import FakeProvider, ProviderFailure, ProviderText, ProviderToolCall
from kisansathi_auth.claims import ActorScope


class FakeExecutor:
    async def execute(self, tool, arguments, actor, **kwargs):
        return {"status": "ok", "summary": "authoritative result", "data": {"id": "field-a", "farmer_id": actor.farmer_id}, "request_id": kwargs["request_id"], "action": {"method": "POST", "path": "/v1/fields"}}


def test_authenticated_read_write_reconnect_and_cross_actor_denial() -> None:
    actor = ActorScope("user-a", "tenant-a", "farmer-a", ("farmer",), "session-a")
    other = ActorScope("user-b", "tenant-b", "farmer-b", ("farmer",), "session-b")
    provider = FakeProvider([ProviderText("I found your field."), ProviderToolCall("create_field", {"name": "North"}, "call-a")])
    harness = Orchestrator(provider, tool_executor=FakeExecutor())
    session, cookie, ready = harness.start_session(actor)
    assert cookie and ready.kind == "ready"
    result = asyncio.run(harness.send_turn(actor, session.session_id, "turn-a", [{"role": "user", "content": "show and create"}], workflow="record_update"))
    assert result.status == "awaiting_confirmation"
    assert len(harness.resume(actor, session.session_id, after=0)) >= 2
    with pytest.raises(OrchestratorError) as denied:
        harness.require_session(other, session.session_id)
    assert denied.value.code == "session_forbidden"
    approval = harness.approvals.get(result.approval_id, actor)
    completed = asyncio.run(harness.resolve_approval(actor, session.session_id, result.approval_id, accepted=True, payload_hash=approval.payload_hash, workflow="record_update"))
    assert completed.status == "succeeded"
    assert any(event.kind == "tool" for event in completed.events)


def test_provider_failure_is_typed_and_never_success() -> None:
    actor = ActorScope("user-a", "tenant-a", "farmer-a", ("farmer",), "session-failure")
    harness = Orchestrator(FakeProvider([ProviderFailure("provider_timeout", retryable=True)]))
    session, _, _ = harness.start_session(actor)
    result = asyncio.run(harness.send_turn(actor, session.session_id, "turn-failure", [{"role": "user", "content": "hello"}]))
    assert result.status == "degraded"
    assert any(event.kind == "diagnostic" and event.payload["code"] == "provider_timeout" for event in result.events)
    assert not any(event.kind == "agentMessageCompleted" for event in result.events)
