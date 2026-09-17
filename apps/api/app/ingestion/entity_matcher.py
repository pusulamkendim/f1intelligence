from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class EntityAlias:
    entity_id: UUID
    entity_type: str
    slug: str
    display_name: str
    alias: str
    alias_type: str
    confidence: int
    valid_from_season: int | None = None
    valid_to_season: int | None = None


@dataclass(frozen=True)
class EntityMention:
    entity_id: UUID
    entity_type: str
    slug: str
    display_name: str
    matched_alias: str
    alias_type: str
    confidence: int
    match_method: str = "alias"


def normalize_entity_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    ascii_like = "".join(
        character for character in decomposed if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_like).strip()


def _is_active_for_season(alias: EntityAlias, season: int | None) -> bool:
    if season is None:
        return True
    if alias.valid_from_season is not None and season < alias.valid_from_season:
        return False
    if alias.valid_to_season is not None and season > alias.valid_to_season:
        return False
    return True


def _matches_case_sensitive_token(text: str, value: str) -> bool:
    """Match provider codes such as HAM/VER/FOR without colliding with prose words."""
    token = value.strip()
    if not token:
        return False
    pattern = rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])"
    return re.search(pattern, text) is not None


def match_entities(
    text: str,
    aliases: list[EntityAlias],
    *,
    season: int | None = None,
    race_season: int | None = None,
) -> tuple[EntityMention, ...]:
    """Resolve aliases while allowing race editions to use a distinct season.

    Editorial stories frequently discuss a future calendar while being published in
    the current season. Team/person identity validity should still follow publication
    context, but race aliases must follow the season explicitly referenced by the story.
    """
    normalized_text = normalize_entity_text(text)
    if not normalized_text:
        return ()

    haystack = f" {normalized_text} "
    matches: dict[UUID, tuple[int, int, EntityMention]] = {}

    for alias in aliases:
        alias_season = race_season if alias.entity_type == "race" else season
        if not _is_active_for_season(alias, alias_season):
            continue

        normalized_alias = normalize_entity_text(alias.alias)
        if len(normalized_alias) < 2:
            continue

        if alias.alias_type == "driver_code":
            if not _matches_case_sensitive_token(text, alias.alias):
                continue
        elif f" {normalized_alias} " not in haystack:
            continue

        mention = EntityMention(
            entity_id=alias.entity_id,
            entity_type=alias.entity_type,
            slug=alias.slug,
            display_name=alias.display_name,
            matched_alias=alias.alias,
            alias_type=alias.alias_type,
            confidence=alias.confidence,
        )
        rank = (len(normalized_alias), alias.confidence)
        current = matches.get(alias.entity_id)
        if current is None or rank > current[:2]:
            matches[alias.entity_id] = (*rank, mention)

    mentions = [value[2] for value in matches.values()]
    mentions.sort(key=lambda item: (item.entity_type, item.display_name.casefold()))
    return tuple(mentions)
