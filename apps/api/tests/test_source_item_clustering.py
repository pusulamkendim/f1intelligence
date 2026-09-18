from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.ingestion.source_item_clustering import (
    ClusterFeatures,
    event_fingerprint,
    refresh_cluster_candidates,
    score_same_story,
)


def _features(
    provider: str,
    title: str,
    *,
    strong: frozenset | None = None,
    races: frozenset | None = None,
    published_at: datetime | None = None,
) -> ClusterFeatures:
    return ClusterFeatures(
        provider=provider,
        title=title,
        published_at=published_at,
        strong_entity_ids=strong or frozenset(),
        race_entity_ids=races or frozenset(),
        event_fingerprint=event_fingerprint(title),
    )


def test_exact_cross_source_title_is_a_max_confidence_candidate() -> None:
    title = "Mercedes confirms Mike Elliott as Chief Technical Officer"
    score = score_same_story(
        _features("autosport.com", title),
        _features("motorsport.com", title),
    )
    assert score is not None
    assert score.score == 100
    assert score.method == "exact_title_v3"


def test_calendar_announcement_clusters_without_entities() -> None:
    now = datetime(2026, 9, 16, 9, tzinfo=UTC)
    score = score_same_story(
        _features(
            "formula1.com",
            "2027 Formula 1 race calendar confirmed with 10 Sprint events revealed",
            published_at=now,
        ),
        _features(
            "bbc.com",
            "Formula 1 2027: Calendar to have 10 sprint races next year, including Monaco",
            published_at=now + timedelta(minutes=1),
        ),
    )
    assert score is not None
    assert score.score == 96
    assert score.method == "event_fingerprint_v3"
    assert score.reasons["event_fingerprint"] == "calendar_announcement:2027"


def test_different_calendar_seasons_do_not_cluster() -> None:
    score = score_same_story(
        _features("a.com", "Formula 1 2027 calendar revealed"),
        _features("b.com", "Formula 1 2028 calendar revealed"),
    )
    assert score is None


def test_max_vs_100_named_event_clusters_without_race_entity() -> None:
    now = datetime(2026, 9, 17, 13, 30, tzinfo=UTC)
    score = score_same_story(
        _features(
            "motorsport.com",
            "Max Verstappen surprised himself in karting challenge against 100 competitors",
            published_at=now,
        ),
        _features(
            "bbc.com",
            "Max vs 100: Verstappen overtakes 100 amateur karters in just 14 laps",
            published_at=now - timedelta(hours=19),
        ),
    )
    assert score is not None
    assert score.score == 96
    assert score.method == "event_fingerprint_v3"


def test_elliott_appointment_clusters_even_when_one_title_omits_name() -> None:
    now = datetime(2026, 9, 17, 10, 40, tzinfo=UTC)
    score = score_same_story(
        _features(
            "the-race.com",
            "Alpine hires ex-Mercedes F1 tech chief",
            published_at=now,
        ),
        _features(
            "alpinef1.com",
            "Mike Elliott joins BWT Alpine Formula One Team as Chief Technical Officer",
            published_at=now + timedelta(minutes=4),
        ),
    )
    assert score is not None
    assert score.score == 91
    assert score.method == "event_fingerprint_v3"
    assert (
        score.reasons["event_fingerprint"]
        == "personnel_appointment:alpine:technical_leadership"
    )


def test_two_shared_strong_entities_support_paraphrased_headlines() -> None:
    hamilton, ferrari = uuid4(), uuid4()
    now = datetime(2026, 9, 17, 14, tzinfo=UTC)
    score = score_same_story(
        _features(
            "the-race.com",
            "Hamilton firmly denies asking for Ferrari staff to be replaced",
            strong=frozenset({hamilton, ferrari}),
            published_at=now,
        ),
        _features(
            "motorsport.com",
            "Lewis Hamilton denies claims he is pushing Ferrari to replace key staff",
            strong=frozenset({hamilton, ferrari}),
            published_at=now + timedelta(minutes=26),
        ),
    )
    assert score is not None
    assert score.score >= 90
    assert score.method == "multi_entity_title_v3"


def test_related_but_distinct_two_entity_story_stays_rejected() -> None:
    tsunoda, red_bull = uuid4(), uuid4()
    now = datetime(2026, 9, 17, 6, tzinfo=UTC)
    score = score_same_story(
        _features(
            "racefans.net",
            "Tsunoda wasn’t hugely disappointed when Red Bull dropped him last year",
            strong=frozenset({tsunoda, red_bull}),
            published_at=now,
        ),
        _features(
            "autosport.com",
            "Tsunoda's in-depth look at why he failed to master Red Bull’s F1 car in 2025",
            strong=frozenset({tsunoda, red_bull}),
            published_at=now + timedelta(hours=3),
        ),
    )
    assert score is None


def test_single_shared_entity_needs_high_title_similarity() -> None:
    alpine = uuid4()
    score = score_same_story(
        _features(
            "bbc.com",
            "Mike Elliott: Former Mercedes design boss Elliott joins Alpine as chief technical officer",
            strong=frozenset({alpine}),
            published_at=datetime(2026, 9, 17, 10, 52, tzinfo=UTC),
        ),
        _features(
            "alpinef1.com",
            "Mike Elliott joins BWT Alpine Formula One Team as Chief Technical Officer",
            strong=frozenset({alpine}),
        ),
    )
    assert score is not None
    assert score.method in {"event_fingerprint_v3", "single_entity_title_v3"}


def test_shared_subject_and_race_can_support_low_lexical_overlap() -> None:
    driver, race = uuid4(), uuid4()
    now = datetime(2026, 9, 17, 13, 30, tzinfo=UTC)
    score = score_same_story(
        _features(
            "motorsport.com",
            "Driver surprised himself with challenge performance",
            strong=frozenset({driver}),
            races=frozenset({race}),
            published_at=now,
        ),
        _features(
            "bbc.com",
            "Driver completes unusual exhibition challenge",
            strong=frozenset({driver}),
            races=frozenset({race}),
            published_at=now - timedelta(hours=19),
        ),
    )
    assert score is not None
    assert score.method == "entity_race_title_v3"


def test_shared_race_alone_does_not_merge_unrelated_stories() -> None:
    madrid = uuid4()
    now = datetime(2026, 9, 17, 12, tzinfo=UTC)
    score = score_same_story(
        _features(
            "racefans.net",
            "Mercedes explains tyre degradation after the Spanish Grand Prix",
            races=frozenset({madrid}),
            published_at=now,
        ),
        _features(
            "the-race.com",
            "Ferrari investigates pit stop delay at the Spanish Grand Prix",
            races=frozenset({madrid}),
            published_at=now,
        ),
    )
    assert score is None


def test_near_match_outside_time_window_is_rejected() -> None:
    mercedes = uuid4()
    now = datetime(2026, 9, 17, 12, tzinfo=UTC)
    score = score_same_story(
        _features(
            "autosport.com",
            "Mercedes confirms major technical leadership change",
            strong=frozenset({mercedes}),
            published_at=now,
        ),
        _features(
            "motorsport.com",
            "Mercedes confirms major technical leadership change for 2027",
            strong=frozenset({mercedes}),
            published_at=now - timedelta(days=10),
        ),
    )
    assert score is None



def test_named_event_fingerprint_survives_historical_replay_window() -> None:
    now = datetime(2026, 9, 17, 12, tzinfo=UTC)
    score = score_same_story(
        _features(
            "formula1.com",
            "2027 Formula 1 race calendar confirmed",
            published_at=now,
        ),
        _features(
            "bbc.com",
            "Formula 1 2027 calendar revealed",
            published_at=now - timedelta(days=45),
        ),
    )

    assert score is not None
    assert score.method == "event_fingerprint_v3"
    assert score.score == 96



class _EmptyMappingsResult:
    def mappings(self):
        return self

    def all(self):
        return []


class _CaptureSession:
    def __init__(self) -> None:
        self.statements: list[str] = []

    async def execute(self, statement, params=None):
        self.statements.append(str(statement))
        return _EmptyMappingsResult()


@pytest.mark.asyncio
async def test_nullable_event_fingerprint_is_explicitly_typed() -> None:
    session = _CaptureSession()
    features = ClusterFeatures(
        provider="example.com",
        title="Generic F1 story without a named event",
        published_at=None,
        strong_entity_ids=frozenset(),
        race_entity_ids=frozenset(),
        event_fingerprint=None,
    )

    written = await refresh_cluster_candidates(
        session,  # type: ignore[arg-type]
        source_item_id=uuid4(),
        features=features,
    )

    assert written == 0
    candidate_sql = session.statements[2]
    assert "CAST(:event_fingerprint AS text) IS NOT NULL" in candidate_sql
    assert (
        "= CAST(:event_fingerprint AS text)"
        in candidate_sql
    )
