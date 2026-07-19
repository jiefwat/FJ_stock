from __future__ import annotations

import asyncio
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from marketdesk.providers.public_market import PublicMarketProvider  # noqa: E402


async def main() -> None:
    provider = PublicMarketProvider()
    equities, indices, sectors = await asyncio.gather(
        provider.fetch_equities(), provider.fetch_indices(), provider.fetch_sectors()
    )
    required_indices = {"SH.000001", "SZ.399001", "SZ.399006", "SH.000300", "SH.000016", "SH.000688"}
    actual_indices = {item.symbol for item in indices}
    assert len(equities.items) >= 5_000, f"A-share universe too small: {len(equities.items)}"
    assert equities.meta.coverage >= 0.90, f"coverage below 90%: {equities.meta.coverage:.1%}"
    assert required_indices <= actual_indices, f"missing indices: {required_indices - actual_indices}"
    assert len(sectors) >= 30, f"sector coverage too small: {len(sectors)}"
    assert all(item.price is None or math.isfinite(item.price) for item in equities.items)
    assert all(item.change_pct is None or math.isfinite(item.change_pct) for item in equities.items)
    assert equities.meta.observed_at.tzinfo is not None
    print(f"live-data ok: equities={len(equities.items)} coverage={equities.meta.coverage:.1%} indices={len(indices)} sectors={len(sectors)} freshness={equities.meta.freshness}")


if __name__ == "__main__":
    asyncio.run(main())
