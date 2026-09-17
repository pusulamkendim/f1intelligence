from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from app.ingestion.entity_matcher import (
    EntityAlias,
    EntityMention,
    match_entities,
    normalize_entity_text,
)


@dataclass(frozen=True)
class SourceItemText:
    title: str
    standfirst: str | None = None
    summary: str | None = None
    body_excerpt: str | None = None
    season: int | None = None
    race_season: int | None = None
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
    classification_method: str = "deterministic_v2"


_SCOPE_PRIORITY = {
    "title": 4,
    "standfirst": 3,
    "summary": 2,
    "body_excerpt": 1,
}
_SEASON_PATTERN = re.compile(r"\b(20(?:2\d|3\d))\b")
_BACKGROUND_TEAM_MARKERS = {"former", "ex", "like"}
_BACKGROUND_PERSON_MARKERS = {"after", "following"}


def infer_race_season(item: SourceItemText) -> int | None:
    """Use an explicit editorial season for race editions, otherwise publication context.

    The title has the strongest signal, followed by standfirst and summary. Body copy is
    deliberately excluded because historical comparisons often mention many seasons.
    """
    if item.race_season is not None:
        return item.race_season
    for value in (item.title, item.standfirst, item.summary):
        if not value:
            continue
        match = _SEASON_PATTERN.search(value)
        if match:
            return int(match.group(1))
    return item.season


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
    race_season = infer_race_season(item)
    return {
        scope: match_entities(
            value,
            aliases,
            season=item.season,
            race_season=race_season,
        )
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


def _title_alias_span(title: str, alias: str) -> tuple[int, int] | None:
    title_tokens = normalize_entity_text(title).split()
    alias_tokens = normalize_entity_text(alias).split()
    if not title_tokens or not alias_tokens:
        return None
    width = len(alias_tokens)
    for start in range(0, len(title_tokens) - width + 1):
        if title_tokens[start : start + width] == alias_tokens:
            return start, start + width
    return None


def _title_person_positions(
    title: str,
    candidates: tuple[SourceItemEntityCandidate, ...],
) -> list[tuple[int, SourceItemEntityCandidate]]:
    positions: list[tuple[int, SourceItemEntityCandidate]] = []
    for candidate in candidates:
        if candidate.entity_type != "person" or "title" not in candidate.detected_in:
            continue
        span = _title_alias_span(title, candidate.strongest_mention.matched_alias)
        if span is not None:
            positions.append((span[0], candidate))
    positions.sort(key=lambda value: value[0])
    return positions


def _semantic_title_relation(
    candidate: SourceItemEntityCandidate,
    item: SourceItemText,
    candidates: tuple[SourceItemEntityCandidate, ...],
) -> str:
    """Apply conservative title semantics instead of treating every title match as subject."""
    span = _title_alias_span(item.title, candidate.strongest_mention.matched_alias)
    if span is None:
        return "subject"

    title_tokens = normalize_entity_text(item.title).split()
    start, end = span
    previous = title_tokens[start - 1] if start > 0 else None
    following = title_tokens[end] if end < len(title_tokens) else None

    if candidate.entity_type == "team":
        # Previous-employer and comparison phrases are background, not story ownership.
        if previous in _BACKGROUND_TEAM_MARKERS:
            return "mentioned"
        # "McLaren driver ..." / "Red Bull driver's ..." signals affiliation.
        if following == "driver":
            return "directly_involved"
        # A person joining a team makes the destination team directly involved.
        if previous in {"join", "joins", "joined"} and _title_person_positions(item.title, candidates):
            return "directly_involved"

    if candidate.entity_type == "person":
        # In "Rosberg proposes ... after Lando Norris setback", the later person is
        # contextual to the proposal rather than a co-subject.
        earlier_people = [
            position
            for position, other in _title_person_positions(item.title, candidates)
            if other.entity_id != candidate.entity_id and position < start
        ]
        if earlier_people:
            segment = set(title_tokens[max(earlier_people) : start])
            if segment.intersection(_BACKGROUND_PERSON_MARKERS):
                return "mentioned"

    return "subject"


def _relation_type(
    candidate: SourceItemEntityCandidate,
    item: SourceItemText,
    candidates: tuple[SourceItemEntityCandidate, ...],
) -> str:
    detected_in = candidate.detected_in
    # Race editions are event context only when prominent in title/standfirst.
    # Historical/body-only circuit references are mentions, not active story context.
    if candidate.entity_type == "race":
        return "context" if {"title", "standfirst"}.intersection(detected_in) else "mentioned"
    if "title" in detected_in:
        return _semantic_title_relation(candidate, item, candidates)
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
    item: SourceItemText,
) -> tuple[SourceItemEntityClassification, ...]:
    """Assign deterministic semantic relations to already-resolved candidates."""
    classifications: list[SourceItemEntityClassification] = []
    for candidate in candidates:
        strongest = candidate.strongest_mention
        relation_type = _relation_type(candidate, item, candidates)
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
    classifications = classify_source_item_entity_candidates(candidates, item)
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
