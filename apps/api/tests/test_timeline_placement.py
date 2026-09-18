import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

import app.timeline.placement as placement_module
from app.timeline.placement import (
    _select_story_race,
    explicit_f1_season,
    explicit_historical_event_year,
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

    async def fake_story_races(session, requested_story_id):
        assert requested_story_id == story_id
        return []

    monkeypatch.setattr(
        placement_module,
        "_story_row",
        fake_story_row,
    )
    monkeypatch.setattr(
        placement_module,
        "_story_races",
        fake_story_races,
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



def _race_candidate(
    slug: str,
    *,
    season: int,
    round_number: int,
    anchor_at: datetime,
    confidence: int,
    matched_alias: str,
) -> dict:
    return {
        "id": uuid4(),
        "season": season,
        "slug": slug,
        "official_name": slug,
        "round": round_number,
        "anchor_at": anchor_at,
        "relation_type": "context",
        "confidence": confidence,
        "matched_alias": matched_alias,
    }


def test_f1_season_parser_rejects_other_series_and_external_events() -> None:
    assert (
        explicit_f1_season("Slater to graduate from F3 to F2 for 2027")
        is None
    )
    assert (
        explicit_f1_season(
            "The Human Engine Project submitted for consideration at SXSW 2027"
        )
        is None
    )
    assert (
        explicit_f1_season(
            "F1 clash avoided but can Norris race at Le Mans 2027?"
        )
        is None
    )
    assert explicit_f1_season("2027 Formula 1 race calendar confirmed") == 2027
    assert explicit_f1_season("Ferrari switches focus to 2027 F1 car") == 2027


def test_historical_event_year_detects_on_this_day_reference() -> None:
    assert (
        explicit_historical_event_year(
            "On this day in 2016, Nico Rosberg won the Singapore GP"
        )
        == 2016
    )


def test_preview_prefers_next_race_over_previous_context() -> None:
    reported = datetime(2026, 9, 10, 12, tzinfo=UTC)
    monza = _race_candidate(
        "2026-italian-grand-prix",
        season=2026,
        round_number=13,
        anchor_at=datetime(2026, 9, 6, 13, tzinfo=UTC),
        confidence=92,
        matched_alias="Monza",
    )
    madrid = _race_candidate(
        "2026-madrid-grand-prix",
        season=2026,
        round_number=14,
        anchor_at=datetime(2026, 9, 13, 13, tzinfo=UTC),
        confidence=90,
        matched_alias="Spanish Grand Prix",
    )

    selected = _select_story_race(
        [monza, madrid],
        text_value=(
            "Expecting a Close-Fought Race in Madrid After Monza Success "
            "– Toto’s Spanish GP Preview"
        ),
        reported_at=reported,
    )

    assert selected is not None
    assert selected["slug"] == "2026-madrid-grand-prix"


def test_historical_singapore_story_rejects_current_season_race() -> None:
    selected = _select_story_race(
        [
            _race_candidate(
                "2026-singapore-grand-prix",
                season=2026,
                round_number=17,
                anchor_at=datetime(2026, 10, 11, 12, tzinfo=UTC),
                confidence=100,
                matched_alias="Singapore GP",
            )
        ],
        text_value=(
            "On this day in 2016, Nico Rosberg won the Singapore GP "
            "after holding off a late charge"
        ),
        reported_at=datetime(2026, 9, 18, tzinfo=UTC),
    )

    assert selected is None


@pytest.mark.parametrize(
    ("title", "alias"),
    [
        (
            "Norris completes first full test in McLaren’s Le Mans Hypercar",
            "Spanish Grand Prix",
        ),
        (
            "Ugochukwu beats Slater to win F3 title",
            "Madring",
        ),
        (
            "F2 adds extra Baku feature race and insists Qatar, Abu Dhabi still on",
            "Baku",
        ),
    ],
)
def test_non_f1_event_stories_do_not_use_incidental_f1_race_context(
    title: str,
    alias: str,
) -> None:
    selected = _select_story_race(
        [
            _race_candidate(
                "2026-madrid-grand-prix",
                season=2026,
                round_number=14,
                anchor_at=datetime(2026, 9, 13, 13, tzinfo=UTC),
                confidence=90,
                matched_alias=alias,
            )
        ],
        text_value=title,
        reported_at=datetime(2026, 9, 14, tzinfo=UTC),
    )

    assert selected is None


def test_non_f1_future_year_falls_back_to_report_timeline() -> None:
    placement = infer_story_coordinate(
        text_value="Slater to graduate from F3 to F2 for 2027",
        taxonomy="general",
        reported_at=datetime(2026, 9, 15, tzinfo=UTC),
        race_season=None,
        race_anchor_at=None,
    )

    assert placement.season == 2026
    assert placement.precision == "timestamp"
    assert placement.temporal_relation == "reported_at"


def test_f1_future_season_still_maps_to_scheduled_season() -> None:
    placement = infer_story_coordinate(
        text_value="2027 Formula 1 race calendar confirmed",
        taxonomy="sporting",
        reported_at=datetime(2026, 9, 16, tzinfo=UTC),
        race_season=None,
        race_anchor_at=None,
    )

    assert placement.season == 2027
    assert placement.precision == "season"
    assert placement.temporal_relation == "scheduled_for"



def test_non_f1_year_context_beats_aggregate_f1_year_phrase() -> None:
    value = (
        "F1 clash avoided but can Lando Norris or Max Verstappen race at "
        "Le Mans 2027? The wider F1 2027 calendar avoids a direct clash."
    )

    assert explicit_f1_season(value) is None
