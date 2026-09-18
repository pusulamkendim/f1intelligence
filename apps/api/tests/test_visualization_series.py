from app.visualizations.series import lap_time_series, normalize_team_color, position_series, stint_series


def row(**overrides):
    base = {"driver_key": "max-verstappen", "driver_label": "Max Verstappen", "team_key": "red-bull-racing", "team_label": "Red Bull Racing", "team_color": "3671C6"}
    return {**base, **overrides}


def test_position_series_is_deterministic_sorted_and_team_colored():
    rows = [row(lap_number=2, position=1), row(driver_key="lando-norris", driver_label="Lando Norris", team_key="mclaren", team_label="McLaren", team_color="#FF8000", lap_number=1, position=2), row(lap_number=1, position=3)]
    result = position_series(rows)
    assert [s["key"] for s in result] == ["lando-norris", "max-verstappen"]
    assert result[1]["color"] == "#3671C6"
    assert result[1]["points"] == [{"lap": 1, "position": 3}, {"lap": 2, "position": 1}]


def test_team_color_normalization_is_conservative():
    assert normalize_team_color("3671c6") == "#3671C6"
    assert normalize_team_color("#FF8000") == "#FF8000"
    assert normalize_team_color("red") is None


def test_lap_time_series_ignores_missing_times():
    result = lap_time_series([row(lap_number=1, lap_duration_seconds=None), row(lap_number=2, lap_duration_seconds=91.25)])
    assert result[0]["points"] == [{"lap": 2, "seconds": 91.25}]


def test_stint_series_preserves_compound_and_range():
    result = stint_series([row(stint_number=1, lap_start=1, lap_end=20, compound="MEDIUM", tyre_age_at_start=0)])
    assert result[0]["points"][0]["compound"] == "MEDIUM"
