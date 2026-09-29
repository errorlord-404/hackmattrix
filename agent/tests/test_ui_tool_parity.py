from __future__ import annotations

import json
import re
from pathlib import Path

import httpx

from kisansathi_agent.backend_client import BackendClient
from kisansathi_agent.config import Settings
from kisansathi_agent.server import build_server


ROOT = Path(__file__).resolve().parents[2]
PARITY_PATH = ROOT / "agent" / "contracts" / "farmer_ui_tool_parity.json"
FARM_STATE_API_PATH = ROOT / "src" / "api" / "farmStateApi.js"


def test_every_electron_mutation_has_a_farmer_tool_or_explicit_human_only_boundary() -> None:
    """Keep the chat-first promise true as the Electron API evolves.

    A new button that mutates backend state must be accessible through a bound,
    confirmed MCP tool, unless it is deliberately restricted (for example,
    credential entry or demo reset). The contract is machine-readable so this
    cannot silently become documentation drift.
    """
    contract = json.loads(PARITY_PATH.read_text(encoding="utf-8"))
    operations = contract["operations"]
    declared_by_api = {operation["manual_api"]: operation for operation in operations}

    source = FARM_STATE_API_PATH.read_text(encoding="utf-8")
    mutations = set(re.findall(
        r"\b([A-Za-z][A-Za-z0-9]+):(?:(?!,\s*[A-Za-z][A-Za-z0-9]+:)[^\n])*?method:\s*['\"](?:POST|PUT|PATCH)['\"]",
        source,
    ))
    assert mutations, "Expected the Electron farm-state API to expose mutations."
    assert mutations <= declared_by_api.keys(), (
        "Add each new farmStateApi mutation to farmer_ui_tool_parity.json before "
        "shipping it so Codex can perform it or it has an intentional boundary. "
        f"Missing: {sorted(mutations - declared_by_api.keys())}"
    )

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    client = BackendClient(
        Settings(backend_url="http://backend.test", farmer_id="farmer-1"),
        transport=httpx.MockTransport(handler),
    )
    try:
        registered_tools = {tool.name for tool in build_server(client)._tool_manager.list_tools()}
    finally:
        import asyncio
        asyncio.run(client.aclose())

    for operation in operations:
        tool_name = operation.get("mcp_tool")
        designation = operation.get("designation")
        if tool_name:
            assert tool_name in registered_tools, (
                f"{operation['manual_api']} maps to unavailable MCP tool {tool_name}."
            )
        else:
            assert designation == "human_only"
            assert operation.get("reason"), (
                f"Human-only action {operation['manual_api']} needs a documented boundary."
            )
