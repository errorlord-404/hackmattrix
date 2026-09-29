from __future__ import annotations

import asyncio
import logging

from .backend_client import BackendClient
from .config import Settings
from .server import build_server


def main() -> None:
    """Run the MCP server over stdio. Protocol output must stay on stdout."""

    logging.basicConfig(level=logging.INFO)
    settings = Settings.from_env()
    client = BackendClient(settings)
    server = build_server(client)
    try:
        server.run("stdio")
    finally:
        asyncio.run(client.aclose())


if __name__ == "__main__":
    main()

