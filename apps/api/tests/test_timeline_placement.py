import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

import app.timeline.placement as placement_module
from app.timeline.placement import (
    explicit_season,
    infer_lap_number,
    infer_session_code,
    infer_stint_number,
    infer_story_coordinate,
    refresh_story_timeline_placement,
)


def test_qualifying_story_maps_to_qualifying_session() -> None:
    reported = datetime(2026, 9, 12, 17, 30, tzinfo=UTC)
    race_start = datetime(2026, 9, 13, 13, 0, tzinfo=UTC)
    placement = infer_story_coordinate(
        text_value="Spanish Grand Prix: Qualifying Recap",
        taxonomy="sporting",
        reported_at=reported,
        race_season=2026,
        race_anchor_at=race_start,
    )

    assert placement.session_code == "qualifying"
    assert placement.precision == "session"
    assert placement.temporal_relation == "occurred_at"


def test_future_race_upgrade_is_scheduled_for_target_race() -> None:
    reported = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)
    singapore = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
    placement = infer_story_coordinate(
        text_value="Ferrari will bring a new floor for the upcoming Singapore Grand Prix",
        taxonomy="technical",
        reported_at=reported,
        race_season=2026,
        race_anchor_at=singapore,
    )

    assert placement.precision == "race"
    assert placement.temporal_relation == "scheduled_for"


def test_future_regulation_is_effective_from_future_season() -> None:
    placement = infer_story_coordinate(
        text_value="FIA confirms regulation change effective for the 2027 Formula 1 season",
        taxonomy="regulation",
        reported_at=datetime(2026, 9, 18, tzinfo=UTC),
        race_season=None,
        race_anchor_at=None,
    )

    assert placement.season == 2027
    assert placement.precision == "season"
    assert placement.temporal_relation == "effective_from"


def test_lap_reference_can_reach_lap_precision() -> None:
    placement = infer_story_coordinate(
        text_value="Norris loses the lead after a VSC on lap 42 of the race",
        taxonomy="sporting",
        reported_at=datetime(2026, 9, 13, 16, tzinfo=UTC),
        race_season=2026,
        race_anchor_at=datetime(2026, 9, 13, 13, tzinfo=UTC),
    )

    assert placement.session_code == "race"
    assert placement.lap_number == 42
    assert placement.precision == "lap"
    assert placement.temporal_relation == "occurred_at"


def test_stint_reference_can_reach_stint_precision() -> None:
    placement = infer_story_coordinate(
        text_value="Piastri's second stint transformed the race",
        taxonomy="sporting",
        reported_at=datetime(2026, 9, 13, 16, tzinfo=UTC),
        race_season=2026,
        race_anchor_at=datetime(2026, 9, 13, 13, tzinfo=UTC),
    )

    assert placement.session_code == "race"
    assert placement.stint_number == 2
    assert placement.precision == "stint"


def test_parsers_are_conservative() -> None:
    assert explicit_season("2027 calendar") == 2027
    assert infer_session_code("Sprint Qualifying report") == "sprint_qualifying"
    assert infer_lap_number("lap 14") == 14
    assert infer_stint_number("stint #3") == 3
    assert infer_lap_number("14 laps remaining") is None



def test_future_regulation_season_overrides_current_race_context() -> None:
    placement = infer_story_coordinate(
        text_value=(
            "FIA confirms a regulation change effective for the 2027 season "
            "after discussions at the 2026 Singapore Grand Prix"
        ),
        taxonomy="regulation",
        reported_at=datetime(2026, 9, 18, tzinfo=UTC),
        race_season=2026,
        race_anchor_at=datetime(2026, 10, 11, 12, tzinfo=UTC),
    )

    assert placement.season == 2027
    assert placement.precision == "season"
    assert placement.temporal_relation == "effective_from"
    assert placement.reason == "explicit_future_effective_season"



class _TimelineCaptureSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        return None


@pytest.mark.asyncio
async def test_timeline_metadata_uses_single_typed_json_bind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    story_id = uuid4()
    reported_at = datetime(2026, 9, 17, 20, 11, tzinfo=UTC)

    async def fake_story_row(session, requested_story_id):
        assert requested_story_id == story_id
        return {
            "id": story_id,
            "title": "2027 Formula 1 season preview",
            "summary": None,
            "taxonomy": "sporting",
            "first_published_at": reported_at,
            "first_observed_at": None,
            "created_at": reported_at,
        }

    async def fake_story_race(session, requested_story_id):
        assert requested_story_id == story_id
        return None

    monkeypatch.setattr(
        placement_module,
        "_story_row",
        fake_story_row,
    )
    monkeypatch.setattr(
        placement_module,
        "_story_race",
        fake_story_race,
    )

    session = _TimelineCaptureSession()
    await refresh_story_timeline_placement(
        session,  # type: ignore[arg-type]
        story_id,
    )

    insert_sql, params = session.calls[-1]
    assert "CAST(:metadata AS jsonb)" in insert_sql
    assert ":reason" not in insert_sql
    assert params is not None
    metadata = json.loads(params["metadata"])
    assert metadata["reason"] == "explicit_season_reference"
    assert metadata["session_code"] is None
    assert metadata["race_key"] is None
    assert metadata["driver_key"] is None



def test_calendar_sprint_count_is_not_a_sprint_session_cue() -> None:
    placement = infer_story_coordinate(
        text_value=(
            "2027 Formula 1 race calendar confirmed "
            "with 10 Sprint events revealed"
        ),
        taxonomy="sporting",
        reported_at=datetime(2026, 9, 18, tzinfo=UTC),
        race_season=None,
        race_anchor_at=None,
    )

    assert placement.session_code is None
    assert placement.season == 2027
    assert placement.precision == "season"
    assert placement.temporal_relation == "scheduled_for"
    assert placement.reason == "explicit_season_reference"
