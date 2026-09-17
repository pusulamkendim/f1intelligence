from decimal import Decimal

import httpx
import pytest

from app.ingestion.jolpica import JolpicaClient, parse_qualifying_results, parse_race_results


def test_parse_race_results_preserves_classification_fields() -> None:
    payload = {"MRData": {"RaceTable": {"Races": [{"Results": [{
        "number": "4", "position": "1", "positionText": "1", "points": "25",
        "Driver": {"driverId": "norris"}, "Constructor": {"constructorId": "mclaren"},
        "grid": "2", "laps": "57", "status": "Finished", "Time": {"time": "1:31:22.123"},
        "FastestLap": {"rank": "2", "lap": "43", "Time": {"time": "1:20.456"}},
    }]}]}}}
    row = parse_race_results(payload)[0]
    assert row.driver_id == "norris"
    assert row.points == Decimal("25")
    assert row.grid_position == 2
    assert row.fastest_lap_number == 43
    assert row.finish_time == "1:31:22.123"


def test_parse_qualifying_results_allows_missing_later_sessions() -> None:
    payload = {"MRData": {"RaceTable": {"Races": [{"QualifyingResults": [{
        "number": "7", "position": "20", "Driver": {"driverId": "example"},
        "Constructor": {"constructorId": "example_team"}, "Q1": "1:24.000",
    }]}]}}}
    row = parse_qualifying_results(payload)[0]
    assert row.position == 20
    assert row.q1 == "1:24.000"
    assert row.q2 is None
    assert row.q3 is None


@pytest.mark.asyncio
async def test_client_uses_round_scoped_result_endpoints() -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, json={"MRData": {"RaceTable": {"Races": []}}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = JolpicaClient(http_client, base_url="https://jolpica.test/ergast/f1")
        assert await client.race_results(2026, 3) == []
        assert await client.qualifying_results(2026, 3) == []

    assert requested == [
        "https://jolpica.test/ergast/f1/2026/3/results.json",
        "https://jolpica.test/ergast/f1/2026/3/qualifying.json",
    ]
