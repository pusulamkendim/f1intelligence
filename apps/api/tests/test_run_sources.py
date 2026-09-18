from app.ingestion.run_sources import (
    SourceStats,
    _reset_transaction_stats,
)


def test_rollback_clears_uncommitted_source_mutation_counters() -> None:
    stats = SourceStats(
        source="example",
        discovered=20,
        fetched=20,
        persisted=5,
        entity_links=9,
        cluster_candidates=2,
        stories_created=1,
        stories_attached=2,
        stories_existing=1,
        stories_merged=1,
        stories_skipped=3,
        failures=4,
    )

    _reset_transaction_stats(stats)

    assert stats.discovered == 20
    assert stats.fetched == 20
    assert stats.persisted == 0
    assert stats.entity_links == 0
    assert stats.cluster_candidates == 0
    assert stats.stories_created == 0
    assert stats.stories_attached == 0
    assert stats.stories_existing == 0
    assert stats.stories_merged == 0
    assert stats.stories_skipped == 0
    assert stats.failures == 4
