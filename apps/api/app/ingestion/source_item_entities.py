from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.ingestion.entity_matcher import EntityAlias, EntityMention, match_entities


@dataclass(frozen=True)
class SourceItemText:
    title: str
    standfirst: str | None = None
    summary: str | None = None
    body_excerpt: str | None = None
    season: int | None = None


@dataclass(frozen=True)
class SourceItemEntityClassification:
    entity_id: UUID
    entity_type: str
    slug: str
    display_name: str
    relation_type: str
    confidence: int
    match_method: str
    matched_alias: str
    detected_in: tuple[str, ...]
    classification_method: str = "deterministic_v1"


_SCOPE_PRIORITY = {
    "title": 4,
    "standfirst": 3,
    "summary": 2,
    "body_excerpt": 1,
}


def _scope_mentions(
    item: SourceItemText,
    aliases: list[EntityAlias],
) -> dict[str, tuple[EntityMention, ...]]:
    fields = {
        "title": item.title,
        "standfirst": item.standfirst,
        "summary": item.summary,
        "body_excerpt": item.body_excerpt,
    }
    return {
        scope: match_entities(value, aliases, season=item.season)
        for scope, value in fields.items()
        if value
    }


def _relation_type(entity_type: str, detected_in: tuple[str, ...]) -> str:
    # Race references define event context rather than article ownership.
    if entity_type == "race":
        return "context"
    if "title" in detected_in:
        return "subject"
    # Repeated prominence across the standfirst/summary/body is strong enough to
    # mark direct involvement without pretending to infer causal "affected" semantics.
    if len(detected_in) >= 2 and (
        "standfirst" in detected_in or "summary" in detected_in
    ):
        return "directly_involved"
    return "mentioned"


def _confidence(
    mention: EntityMention,
    relation_type: str,
    detected_in: tuple[str, ...],
) -> int:
    confidence = mention.confidence
    if "title" in detected_in:
        confidence += 5
    elif len(detected_in) == 1:
        confidence = min(confidence, 90)
    if relation_type == "context" and "title" in detected_in:
        confidence += 2
    return min(100, max(1, confidence))


def classify_source_item_entities(
    item: SourceItemText,
    aliases: list[EntityAlias],
) -> tuple[SourceItemEntityClassification, ...]:
    by_scope = _scope_mentions(item, aliases)
    matches: dict[UUID, list[tuple[str, EntityMention]]] = {}

    for scope, mentions in by_scope.items():
        for mention in mentions:
            matches.setdefault(mention.entity_id, []).append((scope, mention))

    classifications: list[SourceItemEntityClassification] = []
    for entity_matches in matches.values():
        entity_matches.sort(
            key=lambda pair: (
                _SCOPE_PRIORITY[pair[0]],
                len(pair[1].matched_alias),
                pair[1].confidence,
            ),
            reverse=True,
        )
        strongest_scope, strongest = entity_matches[0]
        detected_in = tuple(
            sorted(
                {scope for scope, _mention in entity_matches},
                key=lambda scope: _SCOPE_PRIORITY[scope],
                reverse=True,
            )
        )
        relation_type = _relation_type(strongest.entity_type, detected_in)
        classifications.append(
            SourceItemEntityClassification(
                entity_id=strongest.entity_id,
                entity_type=strongest.entity_type,
                slug=strongest.slug,
                display_name=strongest.display_name,
                relation_type=relation_type,
                confidence=_confidence(strongest, relation_type, detected_in),
                match_method=f"{strongest_scope}_alias",
                matched_alias=strongest.matched_alias,
                detected_in=detected_in,
            )
        )

    classifications.sort(
        key=lambda item: (-item.confidence, item.entity_type, item.display_name.casefold())
    )
    return tuple(classifications)
