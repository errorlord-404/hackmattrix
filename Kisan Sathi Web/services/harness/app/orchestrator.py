from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, AsyncIterator, Mapping, Sequence
from uuid import uuid4

from kisansathi_auth.claims import ActorScope

from policy import DEFAULT_POLICY, WorkflowPolicy
from registry import get_tool

from .approvals import ApprovalError, ApprovalManager, ApprovalRequest, request_digest
from .audit import AuditLog, AuditRecord, redact
from .event_store import EventStore, ResumeWindowExpired
from .provider_runtime import ProviderRuntime
from .providers.fake import FakeProvider, ProviderFailure, ProviderText, ProviderToolCall
from .providers.base import ProviderRequest
from .protocol import EventEnvelope, ResumeSnapshot
from .sessions import HarnessSession, SessionManager, SessionOwnershipError


class OrchestratorError(RuntimeError):
    def __init__(self, code: str, message: str = "The harness operation could not be completed.") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class TurnResult:
    status: str
    turn_id: str
    events: tuple[EventEnvelope, ...]
    approval_id: str | None = None
    result: dict[str, Any] | None = None


class Orchestrator:
    """The trusted owner of policy, approvals, tool execution, and replay."""

    @classmethod
    def from_runtime(cls, runtime: ProviderRuntime, **kwargs: Any) -> "Orchestrator":
        """Construct production orchestration from a validated provider runtime."""
        return cls(provider=runtime.adapter, **kwargs)

    def __init__(self, provider: Any | None = None, *, sessions: SessionManager | None = None, event_store: EventStore | None = None, approvals: ApprovalManager | None = None, audit: AuditLog | None = None, tool_executor: Any | None = None, policy: WorkflowPolicy = DEFAULT_POLICY) -> None:
        self.provider = provider or FakeProvider()
        self.sessions = sessions or SessionManager(secret="harness-session-secret-that-is-long-enough")
        self.events = event_store or EventStore()
        self.approvals = approvals or ApprovalManager()
        self.audit = audit or AuditLog()
        self.tool_executor = tool_executor
        self.policy = policy
        self._approval_results: dict[str, dict[str, Any]] = {}

    def public_capabilities(self) -> dict[str, Any]:
        """Return only safe provider state for an authenticated browser response."""
        capabilities = getattr(self.provider, "capabilities", None)
        if capabilities is None:
            return {"provider": getattr(self.provider, "provider_name", "unknown"), "status": "deterministic"}
        return {
            "provider": capabilities.provider,
            "model": capabilities.model_alias,
            "capabilities": sorted(capabilities.capabilities),
            "max_input_bytes": capabilities.max_input_bytes,
            "max_output_tokens": capabilities.max_output_tokens,
            "status": "configured",
        }

    def start_session(self, actor: ActorScope) -> tuple[HarnessSession, str, EventEnvelope]:
        session, cookie = self.sessions.create(actor)
        event = self.events.append(session.session_id, f"turn-{uuid4().hex}", "ready", {"status": "ready", "resumed": False, "provider": getattr(self.provider, "provider_name", "unknown")})
        return session, cookie, event

    def require_session(self, actor: ActorScope, session_id: str) -> HarnessSession:
        try:
            return self.sessions.require(session_id, actor)
        except SessionOwnershipError as exc:
            raise OrchestratorError("session_forbidden") from exc

    def resume(self, actor: ActorScope, session_id: str, after: int = 0) -> list[EventEnvelope] | ResumeSnapshot:
        self.require_session(actor, session_id)
        try:
            return self.events.replay(session_id, after)
        except ResumeWindowExpired as exc:
            return exc.snapshot

    async def _execute(self, tool: str, arguments: dict[str, Any], actor: ActorScope, *, workflow: str, request_id: str, turn_id: str, call_id: str, approval: Any = None) -> dict[str, Any]:
        if self.tool_executor is None:
            return {"status": "ok", "summary": "Deterministic fake tool result.", "data": {"tool": tool, "arguments": redact(arguments)}, "request_id": request_id, "action": None}
        candidate = self.tool_executor
        if hasattr(candidate, "execute"):
            value = candidate.execute(tool, arguments, actor, workflow=workflow, request_id=request_id, turn_id=turn_id, tool_call_id=call_id, approval=approval)
        else:
            value = candidate(tool, arguments, actor, workflow=workflow, request_id=request_id, turn_id=turn_id, tool_call_id=call_id, approval=approval)
        if inspect.isawaitable(value):
            value = await value
        if not isinstance(value, dict):
            raise OrchestratorError("invalid_tool_result")
        return value

    async def send_turn(self, actor: ActorScope, session_id: str, turn_id: str, messages: Sequence[Mapping[str, str]], *, workflow: str = "farm_context", request_id: str | None = None) -> TurnResult:
        session = self.require_session(actor, session_id)
        try:
            self.sessions.set_turn(session_id, actor, turn_id)
        except ValueError as exc:
            raise OrchestratorError("turn_already_active") from exc
        request_id = request_id or f"request-{uuid4().hex}"
        produced: list[EventEnvelope] = []
        text: list[str] = []
        pending_approval: str | None = None
        try:
            provider_request = ProviderRequest(tuple(dict(message) for message in messages), tuple(self.policy.model_tools(workflow)), request_id)
            stream = self.provider.stream_turn(provider_request) if hasattr(self.provider, "capabilities") else self.provider.stream_turn([dict(message) for message in messages], self.policy.model_tools(workflow))
            async for item in stream:
                if isinstance(item, ProviderText):
                    text.append(item.text)
                    produced.append(self.events.append(session_id, turn_id, "agentMessageDelta", {"text": item.text}))
                    continue
                if isinstance(item, ProviderFailure):
                    produced.append(self.events.append(session_id, turn_id, "diagnostic", {"status": "degraded", "code": item.code, "retryable": item.retryable}))
                    produced.append(self.events.append(session_id, turn_id, "turnCompleted", {"status": "degraded", "provider": getattr(self.provider, "provider_name", "unknown")}))
                    self.sessions.set_turn(session_id, actor, None)
                    return TurnResult("degraded", turn_id, tuple(produced))
                if isinstance(item, ProviderToolCall):
                    try:
                        decision = self.policy.authorize(workflow, item.tool, item.arguments)
                        get_tool(item.tool)
                    except Exception as exc:
                        produced.append(self.events.append(session_id, turn_id, "diagnostic", {"status": "error", "code": "tool_not_allowed"}))
                        produced.append(self.events.append(session_id, turn_id, "turnCompleted", {"status": "error"}))
                        self.sessions.set_turn(session_id, actor, None)
                        return TurnResult("error", turn_id, tuple(produced))
                    if decision.confirmation_required:
                        approval_id = f"approval-{uuid4().hex}"
                        approval = self.approvals.propose(request_id=approval_id, actor=actor, tool=item.tool, arguments=item.arguments)
                        pending_approval = approval.request_id
                        produced.append(self.events.append(session_id, turn_id, "approval", {"request_id": approval.request_id, "tool": approval.tool, "status": approval.status, "payload_hash": approval.payload_hash}))
                        self.audit.record(AuditRecord(actor, request_id, session_id, turn_id, item.call_id, item.tool, "awaiting_confirmation", item.arguments))
                        return TurnResult("awaiting_confirmation", turn_id, tuple(produced), approval_id=approval.request_id)
                    result = await self._execute(item.tool, item.arguments, actor, workflow=workflow, request_id=request_id, turn_id=turn_id, call_id=item.call_id)
                    produced.append(self.events.append(session_id, turn_id, "tool", {"tool": item.tool, "status": result.get("status", "ok"), "result": redact(result)}))
                    self.audit.record(AuditRecord(actor, request_id, session_id, turn_id, item.call_id, item.tool, "executed", item.arguments, result_identity=str(result.get("data", {}).get("id")) if isinstance(result.get("data"), dict) and result.get("data", {}).get("id") else None))
            if text:
                produced.append(self.events.append(session_id, turn_id, "agentMessageCompleted", {"text": "".join(text)}))
            produced.append(self.events.append(session_id, turn_id, "turnCompleted", {"status": "ok"}))
            self.sessions.set_turn(session_id, actor, None)
            return TurnResult("ok", turn_id, tuple(produced))
        except Exception as exc:
            self.sessions.set_turn(session_id, actor, None)
            produced.append(self.events.append(session_id, turn_id, "diagnostic", {"status": "error", "code": "provider_orchestration_failed"}))
            produced.append(self.events.append(session_id, turn_id, "turnCompleted", {"status": "error"}))
            if isinstance(exc, OrchestratorError):
                raise
            return TurnResult("error", turn_id, tuple(produced))

    async def resolve_approval(self, actor: ActorScope, session_id: str, approval_id: str, *, accepted: bool, payload_hash: str, workflow: str = "farm_context", request_id: str | None = None) -> TurnResult:
        session = self.require_session(actor, session_id)
        previous = self._approval_results.get(approval_id)
        if previous is not None:
            return TurnResult(previous["status"], previous["turn_id"], tuple(self.events.replay(session_id, previous["sequence"] - 1)), approval_id=approval_id, result=previous.get("result"))
        approval = self.approvals.resolve(request_id=approval_id, actor=actor, accepted=accepted, payload_hash=payload_hash)
        turn_id = session.active_turn_id or f"turn-{uuid4().hex}"
        events = [self.events.append(session_id, turn_id, "approval", {"request_id": approval_id, "status": approval.status})]
        if not accepted:
            events.append(self.events.append(session_id, turn_id, "turnCompleted", {"status": "declined"}))
            self.sessions.set_turn(session_id, actor, None)
            self.audit.record(AuditRecord(actor, request_id or f"request-{uuid4().hex}", session_id, turn_id, approval_id, approval.tool, "declined", approval.arguments, cancellation=approval.decision_reason))
            result = TurnResult("declined", turn_id, tuple(events), approval_id=approval_id)
            self._approval_results[approval_id] = {"status": result.status, "turn_id": turn_id, "sequence": events[0].sequence}
            return result
        executing = self.approvals.begin_execution(approval_id, actor)
        call_id = f"call-{uuid4().hex}"
        req_id = request_id or f"request-{uuid4().hex}"
        result_payload = await self._execute(executing.tool, executing.arguments, actor, workflow=workflow, request_id=req_id, turn_id=turn_id, call_id=call_id, approval=executing)
        finished = self.approvals.finish(approval_id, actor, succeeded=result_payload.get("status") in {"ok", "degraded"})
        events.append(self.events.append(session_id, turn_id, "tool", {"tool": finished.tool, "status": result_payload.get("status", "error"), "result": redact(result_payload)}))
        events.append(self.events.append(session_id, turn_id, "turnCompleted", {"status": "ok" if finished.status == "succeeded" else "error"}))
        self.sessions.set_turn(session_id, actor, None)
        self.audit.record(AuditRecord(actor, req_id, session_id, turn_id, call_id, finished.tool, finished.status, finished.arguments, result_identity=str(result_payload.get("data", {}).get("id")) if isinstance(result_payload.get("data"), dict) and result_payload.get("data", {}).get("id") else None))
        result = TurnResult("succeeded" if finished.status == "succeeded" else "failed", turn_id, tuple(events), approval_id=approval_id, result=result_payload)
        self._approval_results[approval_id] = {"status": result.status, "turn_id": turn_id, "sequence": events[0].sequence, "result": result_payload}
        return result

    async def cancel(self, actor: ActorScope, session_id: str, turn_id: str) -> EventEnvelope:
        self.require_session(actor, session_id)
        if hasattr(self.provider, "cancel"):
            await self.provider.cancel(turn_id)
        self.sessions.set_turn(session_id, actor, None)
        return self.events.append(session_id, turn_id, "cancelled", {"reason": "farmer_requested"})
