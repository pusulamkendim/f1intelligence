from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256
from uuid import UUID
from xml.etree import ElementTree


@dataclass(frozen=True)
class FeedItem:
    external_id: str
    title: str
    url: str | None
    published_at: datetime | None
    categories: tuple[str, ...]


@dataclass(frozen=True)
class MatchTerm:
    term: str
    weight: int


@dataclass(frozen=True)
class StoryRule:
    story_id: UUID
    slug: str
    min_score: int
    terms: tuple[MatchTerm, ...]


@dataclass(frozen=True)
class StoryMatch:
    story_id: UUID | None
    story_slug: str | None
    score: int
    status: str


def _text(node: ElementTree.Element, tag: str) -> str | None:
    child = node.find(tag)
    if child is None or child.text is None:
        return None
    value = child.text.strip()
    return value or None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def parse_fia_rss(xml_text: str) -> list[FeedItem]:
    root = ElementTree.fromstring(xml_text)
    items: list[FeedItem] = []

    for node in root.findall(".//item"):
        title = _text(node, "title")
        if not title:
            continue

        url = _text(node, "link")
        guid = _text(node, "guid")
        published_at = _parse_date(_text(node, "pubDate"))
        categories = tuple(
            child.text.strip()
            for child in node.findall("category")
            if child.text and child.text.strip()
        )

        fallback_key = f"{url or ''}|{title}|{published_at.isoformat() if published_at else ''}"
        external_id = guid or url or sha256(fallback_key.encode()).hexdigest()

        items.append(
            FeedItem(
                external_id=external_id,
                title=title,
                url=url,
                published_at=published_at,
                categories=categories,
            )
        )

    return items


def score_item(item: FeedItem, rule: StoryRule) -> int:
    searchable = " ".join((item.title, *item.categories)).casefold()
    return sum(term.weight for term in rule.terms if term.term.casefold() in searchable)


def choose_story(item: FeedItem, rules: list[StoryRule]) -> StoryMatch:
    eligible: list[tuple[int, StoryRule]] = []

    for rule in rules:
        score = score_item(item, rule)
        if score >= rule.min_score:
            eligible.append((score, rule))

    if not eligible:
        return StoryMatch(story_id=None, story_slug=None, score=0, status="unmatched")

    eligible.sort(key=lambda pair: pair[0], reverse=True)
    top_score, top_rule = eligible[0]

    if len(eligible) > 1 and eligible[1][0] == top_score:
        return StoryMatch(story_id=None, story_slug=None, score=top_score, status="ambiguous")

    return StoryMatch(
        story_id=top_rule.story_id,
        story_slug=top_rule.slug,
        score=top_score,
        status="matched",
    )
