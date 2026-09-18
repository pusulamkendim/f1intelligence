from uuid import UUID

from app.ingestion.media_assets import (
    _story_match_is_strong_enough,
    infer_content_role,
)
from app.ingestion.media_source_registry import policy_for_provider
from app.media.storage import media_object_key


def test_media_roles_cover_storytelling_categories() -> None:
    assert infer_content_role("The leaders battle for position") == "overtake"
    assert infer_content_role("Crash at Turn 1") == "incident"
    assert infer_content_role("Champagne on the podium") == "podium"
    assert infer_content_role("Mechanics prepare the car in the garage") == "garage"


def test_f1_fansite_is_metadata_only_discovery_source() -> None:
    policy = policy_for_provider("f1-fansite.com")
    assert policy.source_role == "discovery"
    assert policy.storage_policy == "metadata_only"
    assert policy.rights_status == "restricted"


def test_r2_object_keys_are_immutable_asset_scoped() -> None:
    asset_id = UUID("12345678-1234-5678-1234-567812345678")
    assert media_object_key(
        season=2026,
        race_slug="2026-monaco-grand-prix",
        asset_id=asset_id,
        variant="original",
        extension=".jpg",
    ) == (
        "2026/2026-monaco-grand-prix/assets/"
        "12345678-1234-5678-1234-567812345678/original.jpg"
    )



def test_generic_race_only_media_does_not_auto_match_story() -> None:
    assert not _story_match_is_strong_enough(
        role="generic",
        shared_entities=1,
        shared_races=1,
    )


def test_event_media_can_match_on_race_alone() -> None:
    assert _story_match_is_strong_enough(
        role="podium",
        shared_entities=1,
        shared_races=1,
    )


def test_multi_entity_media_can_match_without_event_role() -> None:
    assert _story_match_is_strong_enough(
        role="generic",
        shared_entities=2,
        shared_races=1,
    )



def test_official_team_media_sources_are_metadata_only_until_rights_verified() -> None:
    for provider in ("williamsf1.com", "media.alpinecars.com"):
        policy = policy_for_provider(provider)
        assert policy.source_role == "discovery"
        assert policy.storage_policy == "metadata_only"
        assert policy.rights_status == "restricted"
