from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.ingestion.jolpica import (
    JolpicaCircuit,
    JolpicaQualifyingResult,
    JolpicaRace,
    JolpicaRaceResult,
)
from app.ingestion.run_jolpica import _candidate_rounds, _fetch_completed_rounds, _source_url


def _race(round_number: int, start_at: datetime | None, race_date: date) -> JolpicaRace:
    return JolpicaRace(
        season=2026,
        round=round_number,
        name=f"Round {round_number}",
        race_date=race_date,
        start_at=start_at,
        source_url=None,
        circuit=JolpicaCircuit(
            provider_id=f"circuit-{round_number}",
            name="Test Circuit",
            locality=None,
            country=None,
            latitude=None,
            longitude=None,
            source_url=None,
        ),
    )


def _result(driver_id: str) -> JolpicaRaceResult:
    return JolpicaRaceResult(
        position=1,
        position_text="1",
        points=Decimal("25"),
        driver_id=driver_id,
        constructor_id="test-team",
        car_number=1,
        grid_position=1,
        laps=50,
        status="Finished",
        finish_time="1:30:00.000",
        fastest_lap_rank=1,
        fastest_lap_number=40,
        fastest_lap_time="1:20.000",
    )


def _qualifying(driver_id: str) -> JolpicaQualifyingResult:
    return JolpicaQualifyingResult(
        position=1,
        driver_id=driver_id,
        constructor_id="test-team",
        car_number=1,
        q1="1:21.000",
        q2="1:20.500",
        q3="1:20.000",
    )


def test_candidate_rounds_only_include_races_that_have_started() -> None:
    now = datetime(2026, 9, 17, 12, tzinfo=UTC)
    calendar = [
        _race(1, datetime(2026, 9, 1, 12, tzinfo=UTC), date(2026, 9, 1)),
        _race(2, datetime(2026, 9, 20, 12, tzinfo=UTC), date(2026, 9, 20)),
        _race(3, None, date(2026, 9, 10)),
    ]

    assert _candidate_rounds(calendar, None, now) == [1, 3]


def test_explicit_round_is_allowed_but_must_exist_in_calendar() -> None:
    calendar = [_race(1, None, date(2026, 3, 1)), _race(2, None, date(2026, 3, 8))]

    assert _candidate_rounds(calendar, 2) == [2]
    with pytest.raises(ValueError, match="not present"):
        _candidate_rounds(calendar, 3)


@pytest.mark.asyncio
async def test_completed_round_fetch_skips_rounds_without_race_results() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.qualifying_calls: list[int] = []

        async def race_results(self, season: int, round_number: int):
            assert season == 2026
            return [_result("driver-1")] if round_number == 1 else []

        async def qualifying_results(self, season: int, round_number: int):
            assert season == 2026
            self.qualifying_calls.append(round_number)
            return [_qualifying("driver-1")]

    client = FakeClient()
    completed = await _fetch_completed_rounds(client, 2026, [1, 2])  # type: ignore[arg-type]

    assert [item[0] for item in completed] == [1]
    assert client.qualifying_calls == [1]


def test_result_source_urls_are_round_scoped() -> None:
    assert _source_url(2026, "race_results", 4).endswith("/2026/4/results.json")
    assert _source_url(2026, "qualifying_results", 4).endswith("/2026/4/qualifying.json")
