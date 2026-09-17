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
from app.ingestion.jolpica_sync_state import imported_result_rounds

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


def _rounds_to_fetch(
    candidate_rounds: list[int],
    imported_rounds: set[int],
    round_number: int | None,
) -> list[int]:
    if round_number is not None:
        return [round_number]
    if not candidate_rounds:
        return []

    candidates = set(candidate_rounds)
    missing = candidates - imported_rounds
    # Always refresh the latest started round so late corrections are picked up.
    missing.add(max(candidate_rounds))
    return sorted(missing)


async def _fetch_completed_round(
    client: JolpicaClient,
    season: int,
    round_number: int,
) -> CompletedRound | None:
    race_results = await client.race_results(season, round_number)
    if not race_results:
        return None
    qualifying_results = await client.qualifying_results(season, round_number)
    return round_number, race_results, qualifying_results


async def _persist_completed_round(
    completed: CompletedRound,
    season: int,
) -> tuple[int, int]:
    completed_round, race_results, qualifying_results = completed
    async with SessionLocal() as session:
        async with session.begin():
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
    return race_written, qualifying_written


async def sync_jolpica(season: int, round_number: int | None = None) -> dict[str, object]:
    race_results_written = 0
    qualifying_results_written = 0
    fetched_completed_rounds: list[int] = []

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        client = JolpicaClient(http_client)
        calendar = await client.season_calendar(season)
        candidates = _candidate_rounds(calendar, round_number)

        async with SessionLocal() as session:
            async with session.begin():
                calendar_written = await upsert_calendar(session, calendar)
                already_imported = await imported_result_rounds(session, season)
                await record_sync_run(
                    session,
                    dataset="calendar",
                    season=season,
                    round_number=None,
                    source_url=_source_url(season, "calendar"),
                    records_seen=len(calendar),
                    records_written=calendar_written,
                )

        rounds_to_fetch = _rounds_to_fetch(candidates, already_imported, round_number)
        completed_round_numbers = set(already_imported)

        for candidate_round in rounds_to_fetch:
            completed = await _fetch_completed_round(client, season, candidate_round)
            if completed is None:
                continue
            race_written, qualifying_written = await _persist_completed_round(completed, season)
            race_results_written += race_written
            qualifying_results_written += qualifying_written
            completed_round_numbers.add(candidate_round)
            fetched_completed_rounds.append(candidate_round)

        if round_number is not None and round_number not in completed_round_numbers:
            raise ValueError(f"no completed race results are available for round {round_number}")
        if not completed_round_numbers:
            raise ValueError("no completed race results are available for the season")

        resolved_round = max(completed_round_numbers)
        drivers = await client.driver_standings(season, resolved_round)
        constructors = await client.constructor_standings(season, resolved_round)

    async with SessionLocal() as session:
        async with session.begin():
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
        "completed_rounds": sorted(completed_round_numbers),
        "fetched_completed_rounds": fetched_completed_rounds,
        "cached_completed_rounds": sorted(already_imported),
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
