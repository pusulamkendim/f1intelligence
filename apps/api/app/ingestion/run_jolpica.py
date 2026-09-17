from __future__ import annotations

import argparse
import asyncio

import httpx

from app.db.session import SessionLocal
from app.ingestion.jolpica import JOLPICA_BASE_URL, JolpicaClient
from app.ingestion.jolpica_store import (
    record_sync_run,
    store_constructor_standings,
    store_driver_standings,
    upsert_calendar,
)


def _source_url(season: int, dataset: str, round_number: int | None = None) -> str:
    scope = f"{season}/{round_number}" if round_number is not None else str(season)
    suffix = {
        "calendar": ".json",
        "driver_standings": "/driverstandings.json",
        "constructor_standings": "/constructorstandings.json",
    }[dataset]
    return f"{JOLPICA_BASE_URL}/{scope}{suffix}"


async def sync_jolpica(season: int, round_number: int | None = None) -> None:
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        client = JolpicaClient(http_client)
        calendar = await client.season_calendar(season)
        drivers = await client.driver_standings(season, round_number)
        constructors = await client.constructor_standings(season, round_number)

    resolved_round = round_number
    if resolved_round is None:
        completed_rounds = [race.round for race in calendar if race.start_at is not None]
        if completed_rounds:
            resolved_round = max(completed_rounds)
    if resolved_round is None:
        raise ValueError("round_number is required before the first race of a season")

    async with SessionLocal() as session:
        async with session.begin():
            calendar_written = await upsert_calendar(session, calendar)
            driver_written = await store_driver_standings(
                session,
                season,
                resolved_round,
                drivers,
                _source_url(season, "driver_standings", round_number),
            )
            constructor_written = await store_constructor_standings(
                session,
                season,
                resolved_round,
                constructors,
                _source_url(season, "constructor_standings", round_number),
            )
            await record_sync_run(
                session,
                dataset="calendar",
                season=season,
                round_number=None,
                source_url=_source_url(season, "calendar"),
                records_seen=len(calendar),
                records_written=calendar_written,
            )
            await record_sync_run(
                session,
                dataset="driver_standings",
                season=season,
                round_number=resolved_round,
                source_url=_source_url(season, "driver_standings", round_number),
                records_seen=len(drivers),
                records_written=len(drivers) if driver_written else 0,
                metadata={"snapshot_created": driver_written},
            )
            await record_sync_run(
                session,
                dataset="constructor_standings",
                season=season,
                round_number=resolved_round,
                source_url=_source_url(season, "constructor_standings", round_number),
                records_seen=len(constructors),
                records_written=len(constructors) if constructor_written else 0,
                metadata={"snapshot_created": constructor_written},
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync canonical F1 data from Jolpica")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--round", dest="round_number", type=int)
    args = parser.parse_args()
    asyncio.run(sync_jolpica(args.season, args.round_number))


if __name__ == "__main__":
    main()
