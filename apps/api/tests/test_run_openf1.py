from datetime import UTC, datetime

from app.ingestion.openf1 import OpenF1Session
from app.ingestion.run_openf1 import _result_candidates


def _session(key: int, end_hour: int) -> OpenF1Session:
    return OpenF1Session(
        session_key=key,
        meeting_key=10,
        year=2026,
        session_name="Practice 1",
        session_type="Practice",
        session_code="practice_1",
        circuit_key=None,
        circuit_short_name=None,
        country_name=None,
        location=None,
        date_start=datetime(2026, 9, 17, end_hour - 1, tzinfo=UTC),
        date_end=datetime(2026, 9, 17, end_hour, tzinfo=UTC),
        gmt_offset=None,
        is_cancelled=False,
    )


def test_result_candidates_skip_cached_but_refresh_latest_completed() -> None:
    sessions = [_session(1, 8), _session(2, 9), _session(3, 10)]
    to_fetch, reused = _result_candidates(
        sessions,
        cached_keys={1, 2, 3},
        now=datetime(2026, 9, 17, 12, tzinfo=UTC),
    )

    assert [item.session_key for item in to_fetch] == [3]
    assert reused == [1, 2, 3]


def test_result_candidates_do_not_fetch_sessions_inside_live_window() -> None:
    sessions = [_session(1, 10), _session(2, 12)]
    to_fetch, _ = _result_candidates(
        sessions,
        cached_keys=set(),
        now=datetime(2026, 9, 17, 12, 15, tzinfo=UTC),
    )

    assert [item.session_key for item in to_fetch] == [1]
