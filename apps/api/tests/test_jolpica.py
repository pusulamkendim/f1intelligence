from decimal import Decimal

import httpx
import pytest

from app.ingestion.jolpica import (
    JolpicaClient,
    parse_calendar,
    parse_constructor_standings,
    parse_driver_standings,
)


def test_parse_calendar_preserves_provider_and_provenance() -> None:
    payload = {
        "MRData": {
            "RaceTable": {
                "Races": [
                    {
                        "season": "2026",
                        "round": "1",
                        "raceName": "Australian Grand Prix",
                        "url": "https://example.test/race",
                        "date": "2026-03-08",
                        "time": "04:00:00Z",
                        "Circuit": {
                            "circuitId": "albert_park",
                            "circuitName": "Albert Park Grand Prix Circuit",
                            "url": "https://example.test/circuit",
                            "Location": {
                                "lat": "-37.8497",
                                "long": "144.968",
                                "locality": "Melbourne",
                                "country": "Australia",
                            },
                        },
                    }
                ]
            }
        }
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
    payload = {
        "MRData": {
            "StandingsTable": {
                "StandingsLists": [
                    {
                        "DriverStandings": [
                            {
                                "position": "1",
                                "points": "25.5",
                                "wins": "1",
                                "Driver": {
                                    "driverId": "example",
                                    "givenName": "Test",
                                    "familyName": "Driver",
                                    "permanentNumber": "7",
                                    "code": "TST",
                                },
                                "Constructors": [{"constructorId": "example_team"}],
                            }
                        ]
                    }
                ]
            }
        }
    }
    row = parse_driver_standings(payload)[0]
    assert row.points == Decimal("25.5")
    assert row.constructor_ids == ("example_team",)


def test_parse_constructor_standings_empty_snapshot() -> None:
    payload = {"MRData": {"StandingsTable": {"StandingsLists": []}}}
    assert parse_constructor_standings(payload) == []


@pytest.mark.asyncio
async def test_client_uses_round_scoped_driver_standings_endpoint() -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, json={"MRData": {"StandingsTable": {"StandingsLists": []}}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = JolpicaClient(
            http_client,
            base_url="https://jolpica.test/ergast/f1",
            min_interval_seconds=0,
        )
        assert await client.driver_standings(2026, 4) == []

    assert requested == ["https://jolpica.test/ergast/f1/2026/4/driverstandings.json"]


@pytest.mark.asyncio
async def test_client_retries_rate_limit_and_honors_retry_after() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, request=request)
        return httpx.Response(
            200,
            json={"MRData": {"RaceTable": {"Races": []}}},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = JolpicaClient(
            http_client,
            base_url="https://jolpica.test/ergast/f1",
            max_retries=1,
            retry_backoff_seconds=0,
            min_interval_seconds=0,
        )
        assert await client.season_calendar(2026) == []

    assert attempts == 2


@pytest.mark.asyncio
async def test_client_retries_transient_server_error() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(
            200,
            json={"MRData": {"StandingsTable": {"StandingsLists": []}}},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = JolpicaClient(
            http_client,
            base_url="https://jolpica.test/ergast/f1",
            max_retries=1,
            retry_backoff_seconds=0,
            min_interval_seconds=0,
        )
        assert await client.constructor_standings(2026, 3) == []

    assert attempts == 2
