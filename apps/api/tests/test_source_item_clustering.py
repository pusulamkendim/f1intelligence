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
    assert score.method == "exact_title_v2"


def test_two_shared_strong_entities_support_paraphrased_headlines() -> None:
    hamilton = uuid4()
    ferrari = uuid4()
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
    assert score.method == "multi_entity_title_v2"
    assert score.reasons["shared_strong_entities"] == 2


def test_related_but_distinct_two_entity_story_stays_rejected() -> None:
    tsunoda = uuid4()
    red_bull = uuid4()
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
            published_at=None,
        ),
    )

    assert score is not None
    assert score.method == "single_entity_title_v2"


def test_shared_subject_and_race_can_support_low_lexical_overlap() -> None:
    verstappen = uuid4()
    event = uuid4()
    now = datetime(2026, 9, 17, 13, 30, tzinfo=UTC)
    score = score_same_story(
        _features(
            "motorsport.com",
            "Max Verstappen even surprised himself with karting challenge performance",
            strong=frozenset({verstappen}),
            races=frozenset({event}),
            published_at=now,
        ),
        _features(
            "bbc.com",
            "Max vs 100: Verstappen overtakes 100 amateur karters in just 14 laps",
            strong=frozenset({verstappen}),
            races=frozenset({event}),
            published_at=now - timedelta(hours=19),
        ),
    )

    assert score is not None
    assert score.method == "entity_race_title_v2"


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
