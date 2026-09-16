from uuid import uuid4

from app.ingestion.entity_matcher import EntityAlias, match_entities, normalize_entity_text


def alias(
    name: str,
    value: str,
    *,
    entity_type: str = "person",
    confidence: int = 90,
    valid_from_season: int | None = 2026,
    valid_to_season: int | None = 2026,
) -> EntityAlias:
    return EntityAlias(
        entity_id=uuid4(),
        entity_type=entity_type,
        slug=name.casefold().replace(" ", "-"),
        display_name=name,
        alias=value,
        alias_type="test",
        confidence=confidence,
        valid_from_season=valid_from_season,
        valid_to_season=valid_to_season,
    )


def test_normalize_entity_text_removes_diacritics_and_punctuation() -> None:
    assert normalize_entity_text("Sergio Pérez – Cadillac") == "sergio perez cadillac"


def test_matcher_finds_multiple_entities_with_token_boundaries() -> None:
    red_bull = alias("Red Bull Racing", "Red Bull", entity_type="team", confidence=95)
    mclaren = alias("McLaren", "McLaren", entity_type="team", confidence=100)
    hamilton_code = alias("Lewis Hamilton", "HAM", confidence=86)

    matches = match_entities(
        "ICA hearing – McLaren and Red Bull; Hamilton was not named.",
        [red_bull, mclaren, hamilton_code],
        season=2026,
    )

    assert {match.slug for match in matches} == {"mclaren", "red-bull-racing"}


def test_matcher_does_not_match_driver_code_inside_a_name() -> None:
    hamilton_code = alias("Lewis Hamilton", "HAM", confidence=86)

    assert match_entities("Lewis Hamilton statement", [hamilton_code], season=2026) == ()
    assert match_entities("HAM penalty decision", [hamilton_code], season=2026)[0].slug == (
        "lewis-hamilton"
    )


def test_matcher_respects_season_validity() -> None:
    historical = alias(
        "Example Driver",
        "Example",
        valid_from_season=2025,
        valid_to_season=2025,
    )

    assert match_entities("Example driver", [historical], season=2026) == ()
    assert len(match_entities("Example driver", [historical], season=2025)) == 1


def test_matcher_prefers_more_specific_alias_for_same_entity() -> None:
    entity_id = uuid4()
    aliases = [
        EntityAlias(
            entity_id=entity_id,
            entity_type="team",
            slug="red-bull-racing",
            display_name="Red Bull Racing",
            alias="Red Bull",
            alias_type="common",
            confidence=95,
            valid_from_season=2026,
            valid_to_season=2026,
        ),
        EntityAlias(
            entity_id=entity_id,
            entity_type="team",
            slug="red-bull-racing",
            display_name="Red Bull Racing",
            alias="Oracle Red Bull Racing",
            alias_type="common",
            confidence=98,
            valid_from_season=2026,
            valid_to_season=2026,
        ),
    ]

    match = match_entities("Oracle Red Bull Racing update", aliases, season=2026)[0]
    assert match.matched_alias == "Oracle Red Bull Racing"
