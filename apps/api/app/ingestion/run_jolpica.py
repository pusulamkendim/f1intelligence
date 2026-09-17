from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime

import httpx

from app.db.session import SessionLocal
from app.ingestion.jolpica import (
    JOLPICA_BASE_URL,
    JolpicaClient,
    JolpicaQualifyingResult,
    JolpicaRace,
    JolpicaRaceResult,
)
from app.ingestion.jolpica_store import (
    record_sync_run,
    store_constructor_standings,
    store_driver_standings,
    upsert_calendar,
    upsert_qualifying_results,
    upsert_race_results,
)

CompletedRound = tuple[int, list[JolpicaRaceResult], list[JolpicaQualifyingResult]]


def _source_url(season: int, dataset: str, round_number: int | None = None) -> str:
    if dataset == "calendar":
        return f"{JOLPICA_BASE_URL}/{season}.json"
    if round_number is None:
        raise ValueError(f"round_number is required for {dataset}")
    suffix = {
        "driver_standings": "driverstandings.json",
        "constructor_standings": "constructorstandings.json",
        "race_results": "results.json",
        "qualifying_results": "qualifying.json",
    }[dataset]
    return f"{JOLPICA_BASE_URL}/{season}/{round_number}/{suffix}"


def _candidate_rounds(
    calendar: list[JolpicaRace],
    round_number: int | None,
    now: datetime | None = None,
) -> list[int]:
    available_rounds = {race.round for race in calendar}
    if round_number is not None:
        if round_number not in available_rounds:
            raise ValueError(f"round {round_number} is not present in the season calendar")
        return [round_number]

    current = now or datetime.now(UTC)
    candidates: list[int] = []
    for race in calendar:
        if race.start_at is not None:
            if race.start_at <= current:
                candidates.append(race.round)
        elif race.race_date < current.date():
            candidates.append(race.round)
    return sorted(candidates)


async def _fetch_completed_rounds(
    client: JolpicaClient,
    season: int,
    candidate_rounds: list[int],
) -> list[CompletedRound]:
    completed: list[CompletedRound] = []
    for candidate_round in candidate_rounds:
        race_results = await client.race_results(season, candidate_round)
        if not race_results:
            continue
        qualifying_results = await client.qualifying_results(season, candidate_round)
        completed.append((candidate_round, race_results, qualifying_results))
    return completed


async def sync_jolpica(season: int, round_number: int | None = None) -> dict[str, object]:
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        client = JolpicaClient(http_client)
        calendar = await client.season_calendar(season)
        candidates = _candidate_rounds(calendar, round_number)
        completed_rounds = await _fetch_completed_rounds(client, season, candidates)
        if not completed_rounds:
            scope = f"round {round_number}" if round_number is not None else "the season"
            raise ValueError(f"no completed race results are available for {scope}")

        resolved_round = max(item[0] for item in completed_rounds)
        drivers = await client.driver_standings(season, resolved_round)
        constructors = await client.constructor_standings(season, resolved_round)

    race_results_written = 0
    qualifying_results_written = 0
    async with SessionLocal() as session:
        async with session.begin():
            calendar_written = await upsert_calendar(session, calendar)

            for completed_round, race_results, qualifying_results in completed_rounds:
                race_written = await upsert_race_results(
                    session,
                    season,
                    completed_round,
                    race_results,
                    _source_url(season, "race_results", completed_round),
                )
                qualifying_written = await upsert_qualifying_results(
                    session,
                    season,
                    completed_round,
                    qualifying_results,
                    _source_url(season, "qualifying_results", completed_round),
                )
                race_results_written += race_written
                qualifying_results_written += qualifying_written
                await record_sync_run(
                    session,
                    dataset="race_results",
                    season=season,
                    round_number=completed_round,
                    source_url=_source_url(season, "race_results", completed_round),
                    records_seen=len(race_results),
                    records_written=race_written,
                )
                await record_sync_run(
                    session,
                    dataset="qualifying_results",
                    season=season,
                    round_number=completed_round,
                    source_url=_source_url(season, "qualifying_results", completed_round),
                    records_seen=len(qualifying_results),
                    records_written=qualifying_written,
                )

            driver_written = await store_driver_standings(
                session,
                season,
                resolved_round,
                drivers,
                _source_url(season, "driver_standings", resolved_round),
            )
            constructor_written = await store_constructor_standings(
                session,
                season,
                resolved_round,
                constructors,
                _source_url(season, "constructor_standings", resolved_round),
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
                source_url=_source_url(season, "driver_standings", resolved_round),
                records_seen=len(drivers),
                records_written=len(drivers) if driver_written else 0,
                metadata={"snapshot_created": driver_written},
            )
            await record_sync_run(
                session,
                dataset="constructor_standings",
                season=season,
                round_number=resolved_round,
                source_url=_source_url(season, "constructor_standings", resolved_round),
                records_seen=len(constructors),
                records_written=len(constructors) if constructor_written else 0,
                metadata={"snapshot_created": constructor_written},
            )

    return {
        "season": season,
        "completed_rounds": [item[0] for item in completed_rounds],
        "latest_completed_round": resolved_round,
        "calendar_records": len(calendar),
        "race_results_written": race_results_written,
        "qualifying_results_written": qualifying_results_written,
        "driver_standings_rows": len(drivers),
        "constructor_standings_rows": len(constructors),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync canonical F1 data from Jolpica")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--round", dest="round_number", type=int)
    args = parser.parse_args()
    summary = asyncio.run(sync_jolpica(args.season, args.round_number))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
