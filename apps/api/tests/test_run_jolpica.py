from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.ingestion.jolpica import (
    JolpicaCircuit,
    JolpicaQualifyingResult,
    JolpicaRace,
    JolpicaRaceResult,
)
from app.ingestion.run_jolpica import (
    _candidate_rounds,
    _fetch_completed_round,
    _rounds_to_fetch,
    _source_url,
    _sprint_rounds_to_fetch,
)


def _race(
    round_number: int,
    start_at: datetime | None,
    race_date: date,
    *,
    sprint_start_at: datetime | None = None,
) -> JolpicaRace:
    return JolpicaRace(
        season=2026,
        round=round_number,
        name=f"Round {round_number}",
        race_date=race_date,
        start_at=start_at,
        sprint_start_at=sprint_start_at,
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
        _race(
            1,
            datetime(2026, 9, 1, 12, tzinfo=UTC),
            date(2026, 9, 1),
        ),
        _race(
            2,
            datetime(2026, 9, 20, 12, tzinfo=UTC),
            date(2026, 9, 20),
        ),
        _race(3, None, date(2026, 9, 10)),
    ]

    assert _candidate_rounds(calendar, None, now) == [1, 3]


def test_explicit_round_is_allowed_but_must_exist_in_calendar() -> None:
    calendar = [
        _race(1, None, date(2026, 3, 1)),
        _race(2, None, date(2026, 3, 8)),
    ]

    assert _candidate_rounds(calendar, 2) == [2]
    with pytest.raises(ValueError, match="not present"):
        _candidate_rounds(calendar, 3)


def test_incremental_sync_skips_cached_rounds_but_refreshes_latest() -> None:
    candidates = [1, 2, 3, 4, 5]

    assert _rounds_to_fetch(candidates, {1, 2, 3}, None) == [4, 5]
    assert _rounds_to_fetch(
        candidates,
        {1, 2, 3, 4, 5},
        None,
    ) == [5]
    assert _rounds_to_fetch(
        candidates,
        {1, 2, 3, 4, 5},
        2,
    ) == [2]


def test_sprint_sync_can_run_before_main_race_start() -> None:
    now = datetime(2026, 3, 14, 5, tzinfo=UTC)
    calendar = [
        _race(
            2,
            datetime(2026, 3, 15, 7, tzinfo=UTC),
            date(2026, 3, 15),
            sprint_start_at=datetime(
                2026,
                3,
                14,
                3,
                tzinfo=UTC,
            ),
        )
    ]

    assert _candidate_rounds(calendar, None, now) == []
    assert _sprint_rounds_to_fetch(
        calendar,
        set(),
        None,
        now,
    ) == [2]


def test_sprint_sync_skips_already_imported_rounds() -> None:
    now = datetime(2026, 3, 16, 12, tzinfo=UTC)
    calendar = [
        _race(
            2,
            datetime(2026, 3, 15, 7, tzinfo=UTC),
            date(2026, 3, 15),
            sprint_start_at=datetime(
                2026,
                3,
                14,
                3,
                tzinfo=UTC,
            ),
        )
    ]

    assert _sprint_rounds_to_fetch(
        calendar,
        {2},
        None,
        now,
    ) == []


@pytest.mark.asyncio
async def test_completed_round_fetch_skips_round_without_race_results() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.qualifying_calls: list[int] = []

        async def race_results(
            self,
            season: int,
            round_number: int,
        ):
            assert season == 2026
            return (
                [_result("driver-1")]
                if round_number == 1
                else []
            )

        async def qualifying_results(
            self,
            season: int,
            round_number: int,
        ):
            assert season == 2026
            self.qualifying_calls.append(round_number)
            return [_qualifying("driver-1")]

    client = FakeClient()
    completed = await _fetch_completed_round(
        client,  # type: ignore[arg-type]
        2026,
        2,
    )

    assert completed is None
    assert client.qualifying_calls == []


@pytest.mark.asyncio
async def test_completed_round_fetch_includes_qualifying() -> None:
    class FakeClient:
        async def race_results(
            self,
            season: int,
            round_number: int,
        ):
            assert season == 2026
            assert round_number == 1
            return [_result("driver-1")]

        async def qualifying_results(
            self,
            season: int,
            round_number: int,
        ):
            assert season == 2026
            assert round_number == 1
            return [_qualifying("driver-1")]

    completed = await _fetch_completed_round(
        FakeClient(),  # type: ignore[arg-type]
        2026,
        1,
    )

    assert completed is not None
    assert completed[0] == 1
    assert completed[1][0].driver_id == "driver-1"
    assert completed[2][0].driver_id == "driver-1"


def test_result_source_urls_are_round_scoped() -> None:
    assert _source_url(
        2026,
        "race_results",
        4,
    ).endswith("/2026/4/results.json")
    assert _source_url(
        2026,
        "qualifying_results",
        4,
    ).endswith("/2026/4/qualifying.json")
    assert _source_url(
        2026,
        "sprint_results",
        4,
    ).endswith("/2026/4/sprint.json")
