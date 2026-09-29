from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = ROOT / "codex" / "plugins" / "kisansathi"


def _send(process: subprocess.Popen[str], message: dict) -> None:
    assert process.stdin is not None
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()


def _read(process: subprocess.Popen[str]) -> dict:
    assert process.stdout is not None
    line = process.stdout.readline()
    assert line, process.stderr.read() if process.stderr else "MCP server exited without a response"
    return json.loads(line)


def test_plugin_declares_portable_agent_plugin_mcp_configuration() -> None:
    manifest = json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8"))
    mcp_config = json.loads((PLUGIN_ROOT / "mcp.json").read_text(encoding="utf-8"))
    assert manifest["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    assert manifest["name"] == "kisansathi"
    assert mcp_config["$schema"] == "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
    server = mcp_config["mcpServers"]["kisansathi"]
    assert server["command"] == "python"
    assert server["args"] == ["${PLUGIN_ROOT}/run_server.py"]
    assert server["cwd"] == "${PLUGIN_ROOT}"


def test_stdio_server_lists_farmer_safe_tools_without_calling_backend() -> None:
    environment = os.environ | {
        "KISANSATHI_FARMER_ID": "test-farmer",
        "KISANSATHI_BACKEND_URL": "http://127.0.0.1:8000",
        "PYTHONPATH": str(ROOT / "agent" / "src"),
    }
    process = subprocess.Popen(
        [sys.executable, str(PLUGIN_ROOT / "run_server.py")],
        cwd=PLUGIN_ROOT,
        env=environment,
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _send(process, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
        })
        initialized = _read(process)
        assert initialized["result"]["serverInfo"]["name"] == "kisansathi"
        _send(process, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        _send(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools = _read(process)["result"]["tools"]
        names = {tool["name"] for tool in tools}
        assert {"get_farm_overview", "get_soil_health", "get_weather_for_field", "compare_mandis", "recommend_seeds", "find_logistics_providers"} <= names
        assert "farmer_id" not in json.dumps(tools)
        assert len(tools) >= 60
    finally:
        process.terminate()
        process.wait(timeout=10)
