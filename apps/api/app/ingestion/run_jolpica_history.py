from __future__ import annotations

import argparse
import asyncio
import json

from app.ingestion.run_jolpica import sync_jolpica


def historical_seasons(
    start_season: int,
    end_season: int,
) -> list[int]:
    step = 1 if end_season >= start_season else -1
    return list(range(start_season, end_season + step, step))


async def sync_jolpica_history(
    start_season: int,
    end_season: int,
) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    for season in historical_seasons(start_season, end_season):
        summaries.append(await sync_jolpica(season))
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync a range of F1 seasons from Jolpica"
    )
    parser.add_argument("--start-season", type=int, required=True)
    parser.add_argument("--end-season", type=int, required=True)
    args = parser.parse_args()

    summaries = asyncio.run(
        sync_jolpica_history(
            args.start_season,
            args.end_season,
        )
    )
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
