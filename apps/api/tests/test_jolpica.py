from decimal import Decimal

import httpx
import pytest

from app.ingestion.jolpica import JolpicaClient, parse_calendar, parse_constructor_standings, parse_driver_standings


def test_parse_calendar_preserves_provider_and_provenance() -> None:
    payload = {
        "MRData": {"RaceTable": {"Races": [{
            "season": "2026", "round": "1", "raceName": "Australian Grand Prix",
            "url": "https://example.test/race", "date": "2026-03-08", "time": "04:00:00Z",
            "Circuit": {"circuitId": "albert_park", "circuitName": "Albert Park Grand Prix Circuit",
                "url": "https://example.test/circuit", "Location": {"lat": "-37.8497", "long": "144.968", "locality": "Melbourne", "country": "Australia"}}
        }]}}
    }

    race = parse_calendar(payload)[0]
    assert race.season == 2026
    assert race.round == 1
    assert race.circuit.provider_id == "albert_park"
    assert race.circuit.latitude == Decimal("-37.8497")
    assert race.start_at is not None
    assert race.start_at.isoformat() == "2026-03-08T04:00:00+00:00"
    assert race.source_url == "https://example.test/race"


def test_parse_driver_standings_handles_decimal_points() -> None:
    payload = {"MRData": {"StandingsTable": {"StandingsLists": [{"DriverStandings": [{
        "position": "1", "points": "25.5", "wins": "1",
        "Driver": {"driverId": "example", "givenName": "Test", "familyName": "Driver", "permanentNumber": "7", "code": "TST"},
        "Constructors": [{"constructorId": "example_team"}]
    }]}]}}}
    row = parse_driver_standings(payload)[0]
    assert row.points == Decimal("25.5")
    assert row.constructor_ids == ("example_team",)


def test_parse_constructor_standings_empty_snapshot() -> None:
    assert parse_constructor_standings({"MRData": {"StandingsTable": {"StandingsLists": []}}}) == []


@pytest.mark.asyncio
async def test_client_uses_round_scoped_driver_standings_endpoint() -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, json={"MRData": {"StandingsTable": {"StandingsLists": []}}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = JolpicaClient(http_client, base_url="https://jolpica.test/ergast/f1")
        assert await client.driver_standings(2026, 4) == []

    assert requested == ["https://jolpica.test/ergast/f1/2026/4/driverstandings.json"]
