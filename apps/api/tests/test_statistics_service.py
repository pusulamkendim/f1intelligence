import asyncio

from app.statistics.service import _historical_rows, _season_filter


def test_career_statistics_omits_null_season_bind() -> None:
    clause, params = _season_filter("dss.season", None)

    assert clause == ""
    assert params == {}


def test_season_statistics_uses_typed_integer_filter() -> None:
    clause, params = _season_filter("dss.season", 2025)

    assert clause == "AND dss.season = :season"
    assert params == {"season": 2025}



class _EmptyRows:
    def mappings(self):
        return self

    def all(self):
        return []


class _CaptureStatisticsSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, statement, params):
        self.calls.append((str(statement), dict(params)))
        return _EmptyRows()


def test_career_standings_query_interpolates_empty_season_clause() -> None:
    session = _CaptureStatisticsSession()

    asyncio.run(
        _historical_rows(
            session,  # type: ignore[arg-type]
            "00000000-0000-0000-0000-000000000001",
            None,
        )
    )

    standings_sql, standings_params = session.calls[-1]
    assert "{standings_season_clause}" not in standings_sql
    assert ":season" not in standings_sql
    assert standings_params == {
        "entity_id": "00000000-0000-0000-0000-000000000001"
    }
