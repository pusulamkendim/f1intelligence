import pytest

from app.ingestion.jolpica_store import _validated_entity_map


def test_validated_entity_map_returns_all_resolved_ids() -> None:
    resolved = _validated_entity_map(
        {"max_verstappen", "norris"},
        [("max_verstappen", "driver-entity-1"), ("norris", "driver-entity-2")],
        entity_type="driver",
        season=2026,
    )

    assert resolved == {
        "max_verstappen": "driver-entity-1",
        "norris": "driver-entity-2",
    }


def test_validated_entity_map_rejects_unregistered_provider_ids() -> None:
    with pytest.raises(
        ValueError,
        match="missing canonical jolpica driver mappings for season 2026: unknown_driver",
    ):
        _validated_entity_map(
            {"norris", "unknown_driver"},
            [("norris", "driver-entity-2")],
            entity_type="driver",
            season=2026,
        )
