from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

import httpx

JOLPICA_BASE_URL = "https://api.jolpi.ca/ergast/f1"


@dataclass(frozen=True)
class JolpicaCircuit:
    provider_id: str
    name: str
    locality: str | None
    country: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    source_url: str | None


@dataclass(frozen=True)
class JolpicaRace:
    season: int
    round: int
    name: str
    race_date: date
    start_at: datetime | None
    source_url: str | None
    circuit: JolpicaCircuit


@dataclass(frozen=True)
class JolpicaDriverStanding:
    position: int
    points: Decimal
    wins: int
    driver_id: str
    given_name: str
    family_name: str
    permanent_number: int | None
    code: str | None
    constructor_ids: tuple[str, ...]


@dataclass(frozen=True)
class JolpicaConstructorStanding:
    position: int
    points: Decimal
    wins: int
    constructor_id: str
    name: str
    nationality: str | None


@dataclass(frozen=True)
class JolpicaRaceResult:
    position: int | None
    position_text: str
    points: Decimal
    driver_id: str
    constructor_id: str | None
    car_number: int | None
    grid_position: int | None
    laps: int | None
    status: str | None
    finish_time: str | None
    fastest_lap_rank: int | None
    fastest_lap_number: int | None
    fastest_lap_time: str | None


@dataclass(frozen=True)
class JolpicaQualifyingResult:
    position: int
    driver_id: str
    constructor_id: str | None
    car_number: int | None
    q1: str | None
    q2: str | None
    q3: str | None


class JolpicaClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str = JOLPICA_BASE_URL) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")

    async def _get(self, path: str) -> dict[str, Any]:
        response = await self.client.get(f"{self.base_url}/{path.lstrip('/')}")
        response.raise_for_status()
        return response.json()

    async def season_calendar(self, season: int) -> list[JolpicaRace]:
        return parse_calendar(await self._get(f"{season}.json"))

    async def driver_standings(
        self, season: int, round_number: int | None = None
    ) -> list[JolpicaDriverStanding]:
        scope = f"{season}/{round_number}" if round_number is not None else str(season)
        return parse_driver_standings(await self._get(f"{scope}/driverstandings.json"))

    async def constructor_standings(
        self, season: int, round_number: int | None = None
    ) -> list[JolpicaConstructorStanding]:
        scope = f"{season}/{round_number}" if round_number is not None else str(season)
        return parse_constructor_standings(
            await self._get(f"{scope}/constructorstandings.json")
        )

    async def race_results(self, season: int, round_number: int) -> list[JolpicaRaceResult]:
        return parse_race_results(await self._get(f"{season}/{round_number}/results.json"))

    async def qualifying_results(
        self, season: int, round_number: int
    ) -> list[JolpicaQualifyingResult]:
        return parse_qualifying_results(
            await self._get(f"{season}/{round_number}/qualifying.json")
        )


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value))


def _int(value: Any) -> int | None:
    if value in (None, "", "\\N"):
        return None
    return int(value)


def _utc_datetime(date_value: str, time_value: str | None) -> datetime | None:
    if not time_value:
        return None
    parsed_time = time.fromisoformat(time_value.removesuffix("Z"))
    return datetime.combine(date.fromisoformat(date_value), parsed_time, tzinfo=UTC)


def parse_calendar(payload: dict[str, Any]) -> list[JolpicaRace]:
    races = payload["MRData"]["RaceTable"].get("Races", [])
    parsed: list[JolpicaRace] = []
    for item in races:
        circuit = item["Circuit"]
        location = circuit.get("Location", {})
        parsed.append(
            JolpicaRace(
                season=int(item["season"]),
                round=int(item["round"]),
                name=item["raceName"],
                race_date=date.fromisoformat(item["date"]),
                start_at=_utc_datetime(item["date"], item.get("time")),
                source_url=item.get("url"),
                circuit=JolpicaCircuit(
                    provider_id=circuit["circuitId"],
                    name=circuit["circuitName"],
                    locality=location.get("locality"),
                    country=location.get("country"),
                    latitude=_decimal(location.get("lat")),
                    longitude=_decimal(location.get("long")),
                    source_url=circuit.get("url"),
                ),
            )
        )
    return parsed


def _standings_list(payload: dict[str, Any]) -> dict[str, Any] | None:
    lists = payload["MRData"]["StandingsTable"].get("StandingsLists", [])
    return lists[0] if lists else None


def parse_driver_standings(payload: dict[str, Any]) -> list[JolpicaDriverStanding]:
    standings = _standings_list(payload)
    if standings is None:
        return []
    return [
        JolpicaDriverStanding(
            position=int(row["position"]),
            points=Decimal(row["points"]),
            wins=int(row["wins"]),
            driver_id=row["Driver"]["driverId"],
            given_name=row["Driver"]["givenName"],
            family_name=row["Driver"]["familyName"],
            permanent_number=(
                int(row["Driver"]["permanentNumber"])
                if row["Driver"].get("permanentNumber")
                else None
            ),
            code=row["Driver"].get("code"),
            constructor_ids=tuple(
                item["constructorId"] for item in row.get("Constructors", [])
            ),
        )
        for row in standings.get("DriverStandings", [])
    ]


def parse_constructor_standings(payload: dict[str, Any]) -> list[JolpicaConstructorStanding]:
    standings = _standings_list(payload)
    if standings is None:
        return []
    return [
        JolpicaConstructorStanding(
            position=int(row["position"]),
            points=Decimal(row["points"]),
            wins=int(row["wins"]),
            constructor_id=row["Constructor"]["constructorId"],
            name=row["Constructor"]["name"],
            nationality=row["Constructor"].get("nationality"),
        )
        for row in standings.get("ConstructorStandings", [])
    ]


def _race_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    races = payload["MRData"]["RaceTable"].get("Races", [])
    return races[0] if races else None


def parse_race_results(payload: dict[str, Any]) -> list[JolpicaRaceResult]:
    race = _race_payload(payload)
    if race is None:
        return []
    parsed: list[JolpicaRaceResult] = []
    for row in race.get("Results", []):
        fastest = row.get("FastestLap", {})
        parsed.append(
            JolpicaRaceResult(
                position=_int(row.get("position")),
                position_text=row.get("positionText", ""),
                points=Decimal(row.get("points", "0")),
                driver_id=row["Driver"]["driverId"],
                constructor_id=row.get("Constructor", {}).get("constructorId"),
                car_number=_int(row.get("number")),
                grid_position=_int(row.get("grid")),
                laps=_int(row.get("laps")),
                status=row.get("status"),
                finish_time=row.get("Time", {}).get("time"),
                fastest_lap_rank=_int(fastest.get("rank")),
                fastest_lap_number=_int(fastest.get("lap")),
                fastest_lap_time=fastest.get("Time", {}).get("time"),
            )
        )
    return parsed


def parse_qualifying_results(payload: dict[str, Any]) -> list[JolpicaQualifyingResult]:
    race = _race_payload(payload)
    if race is None:
        return []
    return [
        JolpicaQualifyingResult(
            position=int(row["position"]),
            driver_id=row["Driver"]["driverId"],
            constructor_id=row.get("Constructor", {}).get("constructorId"),
            car_number=_int(row.get("number")),
            q1=row.get("Q1"),
            q2=row.get("Q2"),
            q3=row.get("Q3"),
        )
        for row in race.get("QualifyingResults", [])
    ]
