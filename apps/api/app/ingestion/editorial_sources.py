from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256
from html.parser import HTMLParser
from typing import Any, Literal
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

SourceMode = Literal["rss", "listing"]
MAX_EXCERPT_CHARS = 2000


@dataclass(frozen=True)
class EditorialSource:
    key: str
    provider: str
    source_class: str
    mode: SourceMode
    discovery_url: str
    allowed_hosts: tuple[str, ...] = ()
    article_path_pattern: str | None = None
    rights_policy: str = "metadata_summary_excerpt_only"
    team_slug: str | None = None


@dataclass(frozen=True)
class EditorialItem:
    external_id: str
    canonical_url: str
    title: str
    summary: str | None = None
    body_excerpt: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    section: str | None = None
    language: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        payload = "|".join(
            (
                self.canonical_url,
                self.title,
                self.summary or "",
                self.body_excerpt or "",
                self.published_at.isoformat() if self.published_at else "",
            )
        )
        return sha256(payload.encode()).hexdigest()


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def _clean_text(value: Any, *, limit: int = MAX_EXCERPT_CHARS) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    parser = _TextExtractor()
    parser.feed(html.unescape(value))
    parser.close()
    collapsed = " ".join(parser.parts) or " ".join(value.split())
    return collapsed[:limit] if collapsed else None


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except (TypeError, ValueError, OverflowError):
        return None


def _stable_external_id(provider: str, url: str, native_id: str | None = None) -> str:
    if native_id and native_id.strip():
        return native_id.strip()
    return sha256(f"{provider}|{url}".encode()).hexdigest()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _first_child_text(node: ElementTree.Element, names: set[str]) -> str | None:
    for child in node:
        if _local_name(child.tag) in names and child.text and child.text.strip():
            return child.text.strip()
    return None


def parse_feed(xml_text: str, source: EditorialSource) -> list[EditorialItem]:
    root = ElementTree.fromstring(xml_text)
    nodes = [node for node in root.iter() if _local_name(node.tag) in {"item", "entry"}]
    items: list[EditorialItem] = []

    for node in nodes:
        title = _first_child_text(node, {"title"})
        if not title:
            continue

        link = _first_child_text(node, {"link"})
        if not link:
            for child in node:
                if _local_name(child.tag) == "link" and child.attrib.get("href"):
                    link = child.attrib["href"].strip()
                    break
        if not link:
            continue

        native_id = _first_child_text(node, {"guid", "id"})
        published = _first_child_text(node, {"pubdate", "published", "updated", "date"})
        summary = _first_child_text(node, {"description", "summary", "content", "encoded"})
        author = _first_child_text(node, {"creator", "author"})
        categories = [
            child.attrib.get("term") or (child.text.strip() if child.text else "")
            for child in node
            if _local_name(child.tag) == "category"
        ]
        categories = [value for value in categories if value]
        canonical_url = link.split("?", 1)[0].rstrip("/")

        items.append(
            EditorialItem(
                external_id=_stable_external_id(source.provider, canonical_url, native_id),
                canonical_url=canonical_url,
                title=" ".join(title.split()),
                summary=_clean_text(summary),
                author=_clean_text(author, limit=300),
                published_at=_parse_datetime(published),
                section=categories[0] if categories else None,
                raw_metadata={
                    "source_key": source.key,
                    "categories": categories,
                    "feed_url": source.discovery_url,
                    "team_slug": source.team_slug,
                },
            )
        )
    return items


class _ListingParser(HTMLParser):
    def __init__(self, source: EditorialSource) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.pattern = re.compile(source.article_path_pattern) if source.article_path_pattern else None
        self.urls: list[str] = []
        self.seen: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a":
            return
        href = dict(attrs).get("href")
        if not href:
            return
        absolute = urljoin(self.source.discovery_url, href)
        parsed = urlparse(absolute)
        allowed = {host.casefold() for host in self.source.allowed_hosts}
        if allowed and parsed.netloc.casefold() not in allowed:
            return
        if self.pattern and not self.pattern.search(parsed.path):
            return
        canonical = f"{parsed.scheme or 'https'}://{parsed.netloc}{parsed.path.rstrip('/')}"
        if canonical == self.source.discovery_url.rstrip("/") or canonical in self.seen:
            return
        self.seen.add(canonical)
        self.urls.append(canonical)


def discover_listing_urls(html_text: str, source: EditorialSource) -> list[str]:
    parser = _ListingParser(source)
    parser.feed(html_text)
    parser.close()
    return parser.urls


class _MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.canonical_url: str | None = None
        self.language: str | None = None
        self.document_title: str | None = None
        self.first_h1: str | None = None
        self._json_ld = False
        self._json_parts: list[str] = []
        self.json_documents: list[Any] = []
        self._capture_title = False
        self._title_parts: list[str] = []
        self._capture_h1 = False
        self._h1_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.casefold(): value for key, value in attrs if value is not None}
        lower = tag.casefold()
        if lower == "html" and values.get("lang"):
            self.language = values["lang"]
        elif lower == "meta":
            key = values.get("property") or values.get("name")
            content = values.get("content")
            if key and content:
                self.meta[key.casefold()] = content.strip()
        elif lower == "link" and "canonical" in values.get("rel", "").casefold():
            self.canonical_url = values.get("href")
        elif lower == "script" and "ld+json" in values.get("type", "").casefold():
            self._json_ld = True
            self._json_parts = []
        elif lower == "title" and self.document_title is None:
            self._capture_title = True
            self._title_parts = []
        elif lower == "h1" and self.first_h1 is None:
            self._capture_h1 = True
            self._h1_parts = []

    def handle_data(self, data: str) -> None:
        if self._json_ld:
            self._json_parts.append(data)
        if self._capture_title:
            self._title_parts.append(data)
        if self._capture_h1:
            self._h1_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        lower = tag.casefold()
        if lower == "script" and self._json_ld:
            raw = "".join(self._json_parts).strip()
            self._json_ld = False
            self._json_parts = []
            if raw:
                try:
                    self.json_documents.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass
        elif lower == "title" and self._capture_title:
            self._capture_title = False
            value = " ".join("".join(self._title_parts).split())
            self._title_parts = []
            if value:
                self.document_title = value
        elif lower == "h1" and self._capture_h1:
            self._capture_h1 = False
            value = " ".join("".join(self._h1_parts).split())
            self._h1_parts = []
            if value:
                self.first_h1 = value


def _json_nodes(value: Any):
    if isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _json_nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from _json_nodes(item)


def _article_node(documents: list[Any]) -> dict[str, Any]:
    valid_types = {"article", "newsarticle", "reportagenewsarticle", "blogposting"}
    for document in documents:
        for node in _json_nodes(document):
            raw_type = node.get("@type")
            types = {str(raw_type).casefold()} if isinstance(raw_type, str) else {
                str(value).casefold() for value in raw_type or []
            }
            if types.intersection(valid_types):
                return node
    return {}


def _author_name(value: Any) -> str | None:
    if isinstance(value, str):
        return _clean_text(value, limit=300)
    if isinstance(value, dict):
        return _clean_text(value.get("name"), limit=300)
    if isinstance(value, list):
        names = [name for item in value if (name := _author_name(item))]
        return ", ".join(names) or None
    return None


def parse_article_html(html_text: str, *, requested_url: str, source: EditorialSource) -> EditorialItem:
    parser = _MetadataParser()
    parser.feed(html_text)
    parser.close()
    node = _article_node(parser.json_documents)

    canonical_url = str(
        parser.canonical_url or node.get("url") or parser.meta.get("og:url") or requested_url
    ).split("?", 1)[0].rstrip("/")
    title = (
        node.get("headline")
        or parser.meta.get("og:title")
        or parser.meta.get("twitter:title")
        or parser.first_h1
        or parser.document_title
    )
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"{source.key} article has no usable title")

    summary = _clean_text(
        node.get("description") or parser.meta.get("description") or parser.meta.get("og:description")
    )
    body_excerpt = _clean_text(node.get("articleBody"))
    published_at = _parse_datetime(
        node.get("datePublished")
        or parser.meta.get("article:published_time")
        or parser.meta.get("date")
    )
    section = node.get("articleSection") or parser.meta.get("article:section")
    if isinstance(section, list):
        section = ", ".join(str(value) for value in section)
    if not isinstance(section, str):
        section = None

    return EditorialItem(
        external_id=_stable_external_id(source.provider, canonical_url),
        canonical_url=canonical_url,
        title=" ".join(title.split()),
        summary=summary,
        body_excerpt=body_excerpt,
        author=_author_name(node.get("author")) or _clean_text(parser.meta.get("author"), limit=300),
        published_at=published_at,
        section=section,
        language=parser.language,
        raw_metadata={
            "source_key": source.key,
            "article_section": section,
            "team_slug": source.team_slug,
            "og_type": parser.meta.get("og:type"),
            "title_fallback": (
                "h1"
                if title == parser.first_h1
                else "document_title"
                if title == parser.document_title
                else None
            ),
        },
    )
