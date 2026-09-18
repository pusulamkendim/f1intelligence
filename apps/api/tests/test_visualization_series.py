from app.visualizations.series import (
    lap_time_series,
    normalize_team_color,
    position_series,
    sector_series,
    stint_series,
    tyre_semantic_token,
)


def row(**overrides):
    base = {
        "driver_key": "max-verstappen",
        "driver_label": "Max Verstappen",
        "driver_number": 1,
        "driver_acronym": "VER",
        "team_key": "red-bull-racing",
        "team_label": "Red Bull Racing",
        "team_color": "3671C6",
    }
    return {**base, **overrides}


def test_position_series_is_deterministic_sorted_and_team_colored():
    rows = [
        row(lap_number=2, position=1),
        row(
            driver_key="lando-norris",
            driver_label="Lando Norris",
            driver_number=4,
            driver_acronym="NOR",
            team_key="mclaren",
            team_label="McLaren",
            team_color="#FF8000",
            lap_number=1,
            position=2,
        ),
        row(lap_number=1, position=3),
    ]
    result = position_series(rows)
    assert [series["key"] for series in result] == [
        "lando-norris",
        "max-verstappen",
    ]
    assert result[1]["color"] == "#3671C6"
    assert result[1]["driver_acronym"] == "VER"
    assert result[1]["points"] == [
        {"lap": 1, "position": 3},
        {"lap": 2, "position": 1},
    ]


def test_team_color_normalization_is_conservative():
    assert normalize_team_color("3671c6") == "#3671C6"
    assert normalize_team_color("#FF8000") == "#FF8000"
    assert normalize_team_color("red") is None


def test_tyre_semantics_use_familiar_f1_compound_tokens():
    assert tyre_semantic_token("SOFT") == "tyre-soft"
    assert tyre_semantic_token("medium") == "tyre-medium"
    assert tyre_semantic_token("INTERMEDIATE") == "tyre-intermediate"
    assert tyre_semantic_token("unknown") is None


def test_lap_time_series_marks_session_and_personal_bests():
    rows = [
        row(lap_number=1, lap_duration_seconds=92.0, is_pit_out_lap=False),
        row(lap_number=2, lap_duration_seconds=91.25, is_pit_out_lap=False),
        row(
            driver_key="lando-norris",
            driver_label="Lando Norris",
            lap_number=1,
            lap_duration_seconds=91.5,
            is_pit_out_lap=False,
        ),
    ]
    result = lap_time_series(rows)
    max_series = next(s for s in result if s["key"] == "max-verstappen")
    assert max_series["points"][1]["timing_status"] == "purple"
    assert max_series["points"][0]["timing_status"] == "yellow"
    norris = next(s for s in result if s["key"] == "lando-norris")
    assert norris["points"][0]["timing_status"] == "green"


def test_sector_series_uses_purple_green_yellow_timing_semantics():
    rows = [
        row(
            lap_number=1,
            sector_1_duration_seconds=30.0,
            sector_2_duration_seconds=31.0,
            sector_3_duration_seconds=32.0,
        ),
        row(
            lap_number=2,
            sector_1_duration_seconds=29.0,
            sector_2_duration_seconds=30.5,
            sector_3_duration_seconds=31.5,
        ),
        row(
            driver_key="lando-norris",
            driver_label="Lando Norris",
            lap_number=1,
            sector_1_duration_seconds=29.5,
            sector_2_duration_seconds=30.0,
            sector_3_duration_seconds=31.0,
        ),
    ]
    result = sector_series(rows)
    max_series = next(s for s in result if s["key"] == "max-verstappen")
    assert max_series["points"][1]["s1_status"] == "purple"
    assert max_series["points"][1]["s2_status"] == "green"
    norris = next(s for s in result if s["key"] == "lando-norris")
    assert norris["points"][0]["s2_status"] == "purple"


def test_stint_series_preserves_compound_range_and_token():
    result = stint_series(
        [
            row(
                stint_number=1,
                lap_start=1,
                lap_end=20,
                compound="MEDIUM",
                tyre_age_at_start=0,
            )
        ]
    )
    point = result[0]["points"][0]
    assert point["compound"] == "MEDIUM"
    assert point["compound_token"] == "tyre-medium"
