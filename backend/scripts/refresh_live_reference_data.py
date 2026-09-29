"""Refresh official directory data and remove only superseded local directory fixtures.

The cleanup runs only after all requested live sources complete successfully.
This keeps an offline demo's labelled fixtures recoverable when a government
source is temporarily unavailable.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import init_db
from app.models.gov_scheme import GovScheme
from app.models.machinery_rental import MachineryRental
from app.models.marketplace_listing import MarketplaceListing
from app.scraping.service import sync_universal_data


async def main() -> None:
    client = await init_db()
    try:
        result = await sync_universal_data(
            sources=["gov_schemes", "machinery", "marketplace"],
            trigger="live-reference-refresh",
        )
        if result["status"] != "completed":
            raise RuntimeError(f"Live reference refresh was not complete: {result['errors']}")
        await GovScheme.get_pymongo_collection().delete_many({"$or": [
            {"source": "local_demo_seed_not_live"},
            {"name": {"$regex": "local demo|Demo", "$options": "i"}},
        ]})
        await MachineryRental.get_pymongo_collection().delete_many({"source": "local_demo_seed_not_live"})
        await MarketplaceListing.get_pymongo_collection().delete_many({"source": "local_demo_seed_not_live"})
        print("Official reference refresh completed; local scheme, machinery and marketplace fixtures removed.")
        print(result)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
