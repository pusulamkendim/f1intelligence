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
    source_context_team_slug: str | None = None


@dataclass(frozen=True)
class SourceItemEntityCandidate:
    entity_id: UUID
    entity_type: str
    slug: str
    display_name: str
    strongest_scope: str
    strongest_mention: EntityMention
    detected_in: tuple[str, ...]


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


def detect_source_item_entity_candidates(
    item: SourceItemText,
    aliases: list[EntityAlias],
) -> tuple[SourceItemEntityCandidate, ...]:
    """Detect canonical entities without assigning semantic story relations yet."""
    by_scope = _scope_mentions(item, aliases)
    matches: dict[UUID, list[tuple[str, EntityMention]]] = {}

    for scope, mentions in by_scope.items():
        for mention in mentions:
            matches.setdefault(mention.entity_id, []).append((scope, mention))

    candidates: list[SourceItemEntityCandidate] = []
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
        candidates.append(
            SourceItemEntityCandidate(
                entity_id=strongest.entity_id,
                entity_type=strongest.entity_type,
                slug=strongest.slug,
                display_name=strongest.display_name,
                strongest_scope=strongest_scope,
                strongest_mention=strongest,
                detected_in=detected_in,
            )
        )

    candidates.sort(key=lambda item: (item.entity_type, item.display_name.casefold()))
    return tuple(candidates)


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


def classify_source_item_entity_candidates(
    candidates: tuple[SourceItemEntityCandidate, ...],
) -> tuple[SourceItemEntityClassification, ...]:
    """Assign deterministic relations to already-resolved entity candidates."""
    classifications: list[SourceItemEntityClassification] = []
    for candidate in candidates:
        strongest = candidate.strongest_mention
        relation_type = _relation_type(candidate.entity_type, candidate.detected_in)
        classifications.append(
            SourceItemEntityClassification(
                entity_id=candidate.entity_id,
                entity_type=candidate.entity_type,
                slug=candidate.slug,
                display_name=candidate.display_name,
                relation_type=relation_type,
                confidence=_confidence(strongest, relation_type, candidate.detected_in),
                match_method=f"{candidate.strongest_scope}_alias",
                matched_alias=strongest.matched_alias,
                detected_in=candidate.detected_in,
            )
        )
    return tuple(classifications)


def _source_context_aliases(
    item: SourceItemText,
    aliases: list[EntityAlias],
) -> list[EntityAlias]:
    team_slug = item.source_context_team_slug
    if not team_slug:
        return []

    # team_slug comes from our source registry, not free text. It is a trusted
    # canonical identity hint, so do not tie it to publication-year alias validity.
    return [
        alias
        for alias in aliases
        if alias.entity_type == "team" and alias.slug == team_slug
    ]


def _add_source_context(
    item: SourceItemText,
    aliases: list[EntityAlias],
    classifications: tuple[SourceItemEntityClassification, ...],
) -> tuple[SourceItemEntityClassification, ...]:
    context_aliases = _source_context_aliases(item, aliases)
    if not context_aliases:
        return classifications

    context_aliases.sort(key=lambda alias: (alias.confidence, len(alias.alias)), reverse=True)
    context = context_aliases[0]
    if any(classification.entity_id == context.entity_id for classification in classifications):
        # A textual semantic relation is more informative than publisher/source context.
        return classifications

    return classifications + (
        SourceItemEntityClassification(
            entity_id=context.entity_id,
            entity_type=context.entity_type,
            slug=context.slug,
            display_name=context.display_name,
            relation_type="context",
            confidence=100,
            match_method="source_context",
            matched_alias=context.display_name,
            detected_in=("source",),
        ),
    )


def classify_source_item_entities(
    item: SourceItemText,
    aliases: list[EntityAlias],
) -> tuple[SourceItemEntityClassification, ...]:
    candidates = detect_source_item_entity_candidates(item, aliases)
    classifications = classify_source_item_entity_candidates(candidates)
    classifications = _add_source_context(item, aliases, classifications)
    return tuple(
        sorted(
            classifications,
            key=lambda value: (
                -value.confidence,
                value.entity_type,
                value.display_name.casefold(),
            ),
        )
    )
