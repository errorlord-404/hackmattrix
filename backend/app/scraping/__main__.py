from __future__ import annotations

import argparse
import asyncio
import json

from app.core.database import init_db
from app.scraping.service import SUPPORTED_SOURCES, sync_universal_data


async def _main(sources: list[str]) -> None:
    client = await init_db()
    try:
        result = await sync_universal_data(sources=sources, trigger="cli")
        print(json.dumps(result, default=str, indent=2))
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate the shared database from official agriculture sources")
    parser.add_argument(
        "--sources", default=",".join(sorted(SUPPORTED_SOURCES)),
        help=f"Comma-separated sources: {', '.join(sorted(SUPPORTED_SOURCES))}",
    )
    args = parser.parse_args()
    asyncio.run(_main([value.strip() for value in args.sources.split(",") if value.strip()]))


if __name__ == "__main__":
    main()
