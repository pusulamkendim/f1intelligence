from datetime import UTC, datetime, timedelta

from app.ingestion.openf1 import OpenF1Session
from app.ingestion.run_openf1 import _bounded_candidates, _result_candidates, _telemetry_candidates

NOW = datetime(2026, 9, 17, 12, tzinfo=UTC)


def _session(key: int, ended_hours_ago: int) -> OpenF1Session:
    end = NOW - timedelta(hours=ended_hours_ago)
    return OpenF1Session(key, 1, 2026, "Race", "Race", "race", None, None, None, None, end - timedelta(hours=2), end, "+00:00:00", False)


def test_result_candidates_refresh_latest_completed_session() -> None:
    sessions = [_session(1, 10), _session(2, 8), _session(3, 6)]
    candidates, reused = _result_candidates(sessions, {1, 2, 3}, now=NOW)
    assert [row.session_key for row in candidates] == [3]
    assert reused == [1, 2, 3]


def test_bounded_candidates_backfill_oldest_and_refresh_latest() -> None:
    sessions = [_session(1, 10), _session(2, 8), _session(3, 6), _session(4, 4)]
    selected = _bounded_candidates(sessions, {1, 4}, limit=2, now=NOW)
    assert [row.session_key for row in selected] == [2, 4]


def test_telemetry_candidates_share_bounded_policy() -> None:
    sessions = [_session(1, 10), _session(2, 8), _session(3, 6)]
    assert [row.session_key for row in _telemetry_candidates(sessions, {1}, limit=2, now=NOW)] == [2, 3]
