from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

ARTICLE_PATH_RE = re.compile(r"^/en/latest/article/[^?#]+\.[A-Za-z0-9]+/?$")
ARTICLE_ID_RE = re.compile(r"\.([A-Za-z0-9]+)$")
MAX_BODY_EXCERPT_CHARS = 2000
NON_F1_SECTIONS = {"f2", "f3", "f1 academy"}


@dataclass(frozen=True)
class Formula1Article:
    external_id: str
    canonical_url: str
    title: str
    description: str | None = None
    body_excerpt: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    section: str | None = None
    language: str = "en"
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        payload = "|".join(
            (
                self.canonical_url,
                self.title,
                self.description or "",
                self.body_excerpt or "",
                self.published_at.isoformat() if self.published_at else "",
            )
        )
        return sha256(payload.encode()).hexdigest()


class _LatestLinksParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[str] = []
        self._seen: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a":
            return
        href = dict(attrs).get("href")
        if not href:
            return
        absolute = urljoin(self.base_url, href)
        parsed = urlparse(absolute)
        if parsed.netloc.casefold() not in {"formula1.com", "www.formula1.com"}:
            return
        if not ARTICLE_PATH_RE.match(parsed.path):
            return
        canonical = f"https://www.formula1.com{parsed.path.rstrip('/')}"
        if canonical not in self._seen:
            self._seen.add(canonical)
            self.links.append(canonical)


class _ArticleMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.canonical_url: str | None = None
        self.html_lang: str | None = None
        self._in_json_ld = False
        self._json_ld_parts: list[str] = []
        self.json_ld: list[Any] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.casefold(): value for key, value in attrs if value is not None}
        lower_tag = tag.casefold()
        if lower_tag == "html" and values.get("lang"):
            self.html_lang = values["lang"]
        elif lower_tag == "meta":
            key = values.get("property") or values.get("name")
            content = values.get("content")
            if key and content:
                self.meta[key.casefold()] = content.strip()
        elif lower_tag == "link" and values.get("rel", "").casefold() == "canonical":
            self.canonical_url = values.get("href")
        elif lower_tag == "script" and "ld+json" in values.get("type", "").casefold():
            self._in_json_ld = True
            self._json_ld_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "script" or not self._in_json_ld:
            return
        raw = "".join(self._json_ld_parts).strip()
        self._in_json_ld = False
        self._json_ld_parts = []
        if not raw:
            return
        try:
            self.json_ld.append(json.loads(raw))
        except json.JSONDecodeError:
            return

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._json_ld_parts.append(data)


def discover_formula1_article_urls(html_text: str, *, base_url: str) -> list[str]:
    parser = _LatestLinksParser(base_url)
    parser.feed(html_text)
    parser.close()
    return parser.links


def _iter_json_ld_nodes(value: Any):
    if isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _iter_json_ld_nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_json_ld_nodes(item)


def _is_article_node(node: dict[str, Any]) -> bool:
    node_type = node.get("@type")
    if isinstance(node_type, str):
        types = {node_type.casefold()}
    elif isinstance(node_type, list):
        types = {str(value).casefold() for value in node_type}
    else:
        types = set()
    return bool(types.intersection({"article", "newsarticle", "reportagenewsarticle"}))


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None



def _image_value(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        for key in ("url", "contentUrl", "thumbnailUrl"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    if isinstance(value, list):
        for item in value:
            candidate = _image_value(item)
            if candidate:
                return candidate
    return None

def _author_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        name = value.get("name")
        return name.strip() if isinstance(name, str) and name.strip() else None
    if isinstance(value, list):
        names = [name for item in value if (name := _author_name(item))]
        return ", ".join(names) or None
    return None


def _clean_excerpt(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    collapsed = " ".join(value.split())
    if not collapsed:
        return None
    return collapsed[:MAX_BODY_EXCERPT_CHARS]


def _external_id(canonical_url: str) -> str:
    path = urlparse(canonical_url).path.rstrip("/")
    match = ARTICLE_ID_RE.search(path)
    if match:
        return match.group(1)
    return sha256(canonical_url.encode()).hexdigest()


def is_formula1_relevant_article(article: Formula1Article) -> bool:
    if article.section is None:
        return True
    normalized = " ".join(article.section.casefold().split())
    return normalized not in NON_F1_SECTIONS


def parse_formula1_article(html_text: str, *, requested_url: str) -> Formula1Article:
    parser = _ArticleMetadataParser()
    parser.feed(html_text)
    parser.close()

    article_node: dict[str, Any] = {}
    for document in parser.json_ld:
        for node in _iter_json_ld_nodes(document):
            if _is_article_node(node):
                article_node = node
                break
        if article_node:
            break

    canonical_url = (
        parser.canonical_url
        or article_node.get("url")
        or parser.meta.get("og:url")
        or requested_url
    )
    canonical_url = str(canonical_url).split("?", 1)[0].rstrip("/")

    title = (
        article_node.get("headline")
        or parser.meta.get("og:title")
        or parser.meta.get("twitter:title")
    )
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Formula1.com article has no usable title")

    description = (
        article_node.get("description")
        or parser.meta.get("description")
        or parser.meta.get("og:description")
    )
    description = _clean_excerpt(description)
    body_excerpt = _clean_excerpt(article_node.get("articleBody"))
    published_at = _parse_datetime(
        article_node.get("datePublished")
        or parser.meta.get("article:published_time")
        or parser.meta.get("date")
    )
    section = article_node.get("articleSection") or parser.meta.get("article:section")
    if isinstance(section, list):
        section = ", ".join(str(value) for value in section)
    if not isinstance(section, str):
        section = None

    author = _author_name(article_node.get("author")) or parser.meta.get("author")
    language = parser.html_lang or "en"
    json_image = _image_value(article_node.get("image"))
    open_graph_image = parser.meta.get("og:image") or parser.meta.get("twitter:image")
    image_url = urljoin(canonical_url, json_image or open_graph_image) if (json_image or open_graph_image) else None
    image_source = "json_ld" if json_image else "open_graph" if open_graph_image else None

    return Formula1Article(
        external_id=_external_id(canonical_url),
        canonical_url=canonical_url,
        title=" ".join(title.split()),
        description=description,
        body_excerpt=body_excerpt,
        author=author,
        published_at=published_at,
        section=section,
        language=language,
        raw_metadata={
            "article_section": section,
            "og_type": parser.meta.get("og:type"),
            "source": "formula1.com",
            "image_url": image_url,
            "image_source": image_source,
        },
    )
