from app.statistics.service import _season_filter


def test_career_statistics_omits_null_season_bind() -> None:
    clause, params = _season_filter("dss.season", None)

    assert clause == ""
    assert params == {}


def test_season_statistics_uses_typed_integer_filter() -> None:
    clause, params = _season_filter("dss.season", 2025)

    assert clause == "AND dss.season = :season"
    assert params == {"season": 2025}
