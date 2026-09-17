from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.ingestion.source_item_clustering import ClusterFeatures, score_same_story


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
    )


def test_exact_cross_source_title_is_a_max_confidence_candidate() -> None:
    title = "Mercedes confirms Mike Elliott as Chief Technical Officer"
    score = score_same_story(
        _features("autosport.com", title),
        _features("motorsport.com", title),
    )

    assert score is not None
    assert score.score == 100
    assert score.method == "exact_title_v1"


def test_near_title_requires_shared_strong_entity() -> None:
    mercedes = uuid4()
    now = datetime(2026, 9, 17, 12, tzinfo=UTC)
    score = score_same_story(
        _features(
            "autosport.com",
            "Mercedes 2027 development started a while ago as domination continues",
            strong=frozenset({mercedes}),
            published_at=now,
        ),
        _features(
            "motorsport.com",
            "Mercedes says 2027 development started a while ago as dominance continues",
            strong=frozenset({mercedes}),
            published_at=now + timedelta(hours=2),
        ),
    )

    assert score is not None
    assert score.score >= 90
    assert score.method == "title_entity_v1"


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
