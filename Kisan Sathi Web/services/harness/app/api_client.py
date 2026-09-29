from __future__ import annotations

from typing import Any
from uuid import uuid4

from kisansathi_auth.claims import ActorScope

from api_client import ApiClient, ExecutionContext, ActorScope as ToolActorScope


class HarnessApiClient:
    """Builds trusted tool-registry contexts without accepting model identity."""

    def __init__(self, client: ApiClient, *, service_token: str | None = None, actor_context_secret: str | bytes | None = None) -> None:
        self.client = client
        self.service_token = service_token
        self.actor_context_secret = actor_context_secret

    def context(self, actor: ActorScope, *, session_id: str | None = None, turn_id: str | None = None, request_id: str | None = None, tool_call_id: str | None = None) -> ExecutionContext:
        session = session_id or actor.session_id
        if not session or actor.session_id and actor.session_id != session:
            raise ValueError("session must match actor scope")
        tool_actor = ToolActorScope(actor.sub, actor.tenant_id, actor.farmer_id, actor.roles, session)
        return ExecutionContext(actor=tool_actor, request_id=request_id or f"request-{uuid4().hex}", session_id=session, turn_id=turn_id or f"turn-{uuid4().hex}", tool_call_id=tool_call_id or f"call-{uuid4().hex}", service_token=self.service_token)

    async def execute(self, executor: Any, tool_name: str, arguments: dict[str, Any], actor: ActorScope, *, workflow: str, approval: Any = None, context: ExecutionContext | None = None) -> dict[str, Any]:
        trusted = context or self.context(actor)
        return await executor.execute(tool_name, arguments, trusted, workflow=workflow, approval=approval)
