from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from app.ingestion.media_assets import infer_content_role

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".avif")
_SIZE_RE = re.compile(r"[-_](\d{2,4})x(\d{2,4})(?=\.[a-z0-9]+$)", re.IGNORECASE)
_LOW_VALUE_MARKERS = (
    "affiliate",
    "advert",
    "banner",
    "badge",
    "flag",
    "icon",
    "logo",
    "placeholder",
    "sponsor",
    "sprite",
    "thumbnail",
)
_CHALLENGE_MARKERS = (
    "__cf_chl",
    "cf-chl-",
    "verify you are human",
    "checking your browser",
    "cloudflare challenge",
)
_EVENT_RE = re.compile(
    r"\b(20\d{2})\s+(?:(?:Formula\s*One|Formula\s*1|F1)\s+)?"
    r"([A-Za-z][A-Za-z .'-]{2,40}?)\s+Grand\s+Prix\b",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_ALPINE_VARIANT_RE = re.compile(
    r"^([a-f0-9]{32})-([tml])\.jpg(?:\.webp)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class OfficialMediaSource:
    key: str
    provider: str
    discovery_url: str
    allowed_hosts: tuple[str, ...]
    page_path_pattern: str
    team_slug: str | None = None
    rights_evidence_url: str | None = None


@dataclass(frozen=True)
class OfficialMediaItem:
    image_url: str
    page_url: str
    page_title: str | None
    caption: str | None
    alt_text: str | None
    content_role: str
    photographer: str | None = None
    agency: str | None = None
    origin_provider: str | None = None
    origin_asset_id: str | None = None
    rights_note: str | None = None
    season: int | None = None


OFFICIAL_MEDIA_SOURCES: tuple[OfficialMediaSource, ...] = (
    OfficialMediaSource(
        key="formula1",
        provider="formula1.com",
        discovery_url="https://www.formula1.com/en/latest",
        allowed_hosts=("www.formula1.com", "formula1.com"),
        page_path_pattern=r"^/en/latest/article/[^?#]+",
        rights_evidence_url=(
            "https://www.formula1.com/en/information/"
            "guidelines.4EOKE9RRqevL4niTK9kWyt"
        ),
    ),
    OfficialMediaSource(
        key="williams",
        provider="williamsf1.com",
        discovery_url="https://www.williamsf1.com/photos",
        allowed_hosts=("www.williamsf1.com", "williamsf1.com"),
        page_path_pattern=r"^/articles/[0-9a-f-]+/.+",
        team_slug="williams",
        rights_evidence_url="https://www.williamsf1.com/legal",
    ),
    OfficialMediaSource(
        key="alpine",
        provider="media.alpinecars.com",
        discovery_url="https://media.alpinecars.com/?lang=eng",
        allowed_hosts=("media.alpinecars.com", "www.media.alpinecars.com"),
        page_path_pattern=r"^/20\d{2}-formula-one-.+",
        team_slug="alpine",
        rights_evidence_url="https://media.alpinecars.com/?lang=eng",
    ),
)
OFFICIAL_MEDIA_SOURCE_BY_KEY = {source.key: source for source in OFFICIAL_MEDIA_SOURCES}


def access_block_reason(html_text: str, *, response_url: str) -> str | None:
    parsed = urlparse(response_url)
    if "/register/" in parsed.path.casefold() or "/login" in parsed.path.casefold():
        return "login_or_registration_redirect"
    sample = html_text[:100_000].casefold()
    if any(marker in sample for marker in _CHALLENGE_MARKERS):
        return "anti_bot_challenge"
    return None


class _ListingParser(HTMLParser):
    def __init__(self, source: OfficialMediaSource) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.pattern = re.compile(source.page_path_pattern, re.IGNORECASE)
        self.urls: list[str] = []
        self._seen: set[str] = set()

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.casefold() != "a":
            return
        href = dict(attrs).get("href")
        if not href:
            return
        absolute = urljoin(self.source.discovery_url, href)
        parsed = urlparse(absolute)
        if parsed.netloc.casefold() not in {
            host.casefold() for host in self.source.allowed_hosts
        }:
            return
        if not self.pattern.search(parsed.path):
            return
        query = "?lang=eng" if self.source.key == "alpine" else ""
        canonical = f"https://{parsed.netloc}{parsed.path.rstrip('/')}{query}"
        if canonical not in self._seen:
            self._seen.add(canonical)
            self.urls.append(canonical)


def discover_source_pages(
    html_text: str,
    *,
    source: OfficialMediaSource,
) -> list[str]:
    parser = _ListingParser(source)
    parser.feed(html_text)
    parser.close()
    return parser.urls


def _normalize_image_url(value: str, *, base_url: str) -> str:
    absolute = urljoin(base_url, value)
    parsed = urlparse(absolute)
    if parsed.path.casefold() == "/_next/image":
        target = parse_qs(parsed.query).get("url", [None])[0]
        if target:
            absolute = urljoin(base_url, unquote(target))
    return absolute


def _source_allows_image(
    source: OfficialMediaSource | None,
    url: str,
) -> bool:
    if source is None:
        return True
    parsed = urlparse(url)
    host = parsed.netloc.casefold()
    path = parsed.path.casefold()
    if source.key == "williams":
        if host.endswith("mcprod.williamsf1.com") and "/media/catalog/product/" in path:
            return False
    return True


def _srcset_candidates(
    value: str | None,
    *,
    base_url: str,
    source: OfficialMediaSource | None = None,
) -> list[tuple[str, int]]:
    if not value:
        return []
    output: list[tuple[str, int]] = []
    for part in value.split(","):
        bits = part.strip().split()
        if not bits:
            continue
        url = _normalize_image_url(bits[0], base_url=base_url)
        if not _source_allows_image(source, url):
            continue
        width = 0
        if len(bits) > 1 and bits[1].lower().endswith("w"):
            try:
                width = int(bits[1][:-1])
            except ValueError:
                width = 0
        output.append((url, width))
    return output


def _filename_size(url: str) -> tuple[int, int] | None:
    filename = urlparse(url).path.rsplit("/", 1)[-1].casefold()
    match = _SIZE_RE.search(filename)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _low_value_image(url: str, *, width_hint: int = 0) -> bool:
    path = urlparse(url).path.casefold()
    filename = path.rsplit("/", 1)[-1]
    if any(marker in filename for marker in _LOW_VALUE_MARKERS):
        return True
    size = _filename_size(url)
    if size:
        width, height = size
        if width < 700 or height < 350 or width / max(height, 1) >= 3:
            return True
    if width_hint and width_hint < 700:
        return True
    return False


def _image_href(
    value: str | None,
    *,
    base_url: str,
    source: OfficialMediaSource | None = None,
) -> str | None:
    if not value:
        return None
    absolute = _normalize_image_url(value, base_url=base_url)
    clean = urlparse(absolute).path.casefold()
    if not clean.endswith(IMAGE_EXTENSIONS):
        return None
    if not _source_allows_image(source, absolute):
        return None
    return absolute


def _best_img_candidate(
    attrs: dict[str, str],
    *,
    base_url: str,
    source: OfficialMediaSource | None = None,
) -> tuple[str, int] | None:
    candidates: list[tuple[str, int]] = []
    for key in ("srcset", "data-srcset", "data-lazy-srcset"):
        candidates.extend(
            _srcset_candidates(
                attrs.get(key),
                base_url=base_url,
                source=source,
            )
        )

    for key, score in (
        ("data-full-url", 10_000),
        ("data-original", 9_500),
        ("data-src", 100),
        ("data-lazy-src", 90),
        ("src", 10),
    ):
        value = attrs.get(key)
        if value:
            candidate_url = _normalize_image_url(value, base_url=base_url)
            if _source_allows_image(source, candidate_url):
                candidates.append((candidate_url, score))

    candidates = [
        (url, width)
        for url, width in candidates
        if urlparse(url).scheme in {"http", "https"}
        and not _low_value_image(url, width_hint=width)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[1])


def _event_key(value: str | None) -> tuple[int, str] | None:
    if not value:
        return None
    match = _EVENT_RE.search(" ".join(value.split()))
    if not match:
        return None
    year = int(match.group(1))
    name = " ".join(match.group(2).casefold().split())
    return year, name


def _published_year(value: str | None) -> int | None:
    if not value:
        return None
    match = _YEAR_RE.search(value)
    return int(match.group(1)) if match else None


def _asset_family_key(
    url: str,
    *,
    source: OfficialMediaSource | None,
) -> str:
    if source is not None and source.key == "alpine":
        filename = urlparse(url).path.rsplit("/", 1)[-1]
        match = _ALPINE_VARIANT_RE.match(filename)
        if match:
            return f"alpine:{match.group(1).casefold()}"
    return url


def _asset_variant_rank(
    url: str,
    *,
    source: OfficialMediaSource | None,
) -> int:
    if source is not None and source.key == "alpine":
        filename = urlparse(url).path.rsplit("/", 1)[-1]
        match = _ALPINE_VARIANT_RE.match(filename)
        if match:
            return {"t": 1, "m": 2, "l": 3}.get(match.group(2).casefold(), 0)
    size = _filename_size(url)
    if size:
        return size[0] * size[1]
    return 0


def _caption_matches_page_event(
    *,
    source: OfficialMediaSource | None,
    page_title: str | None,
    caption: str | None,
) -> bool:
    page_event = _event_key(page_title)
    caption_event = _event_key(caption)
    if page_event and caption_event and page_event != caption_event:
        return False
    if (
        source is not None
        and source.key == "alpine"
        and page_event
        and caption
        and caption.casefold().startswith("image -")
        and caption_event is None
    ):
        return False
    return True


def _credit_metadata(
    text_value: str | None,
) -> tuple[str | None, str | None, str | None]:
    value = text_value or ""
    photographer = None
    agency = None
    match = re.search(
        r"(?:photo(?:graph)?|image)\s*(?:by|:)\s*([^/|(),]+)(?:[/|]\s*([^(),]+))?",
        value,
        flags=re.IGNORECASE,
    )
    if match:
        photographer = " ".join(match.group(1).split())
        if match.group(2):
            agency = " ".join(match.group(2).split())

    lower = value.casefold()
    if "getty" in lower:
        origin_provider = "getty_images"
    elif "lat images" in lower:
        origin_provider = "lat_images"
    elif "sutton" in lower:
        origin_provider = "sutton_images"
    elif "dppi" in lower:
        origin_provider = "dppi"
    else:
        origin_provider = None
    return photographer, agency, origin_provider


class _PageMediaParser(HTMLParser):
    def __init__(
        self,
        page_url: str,
        source: OfficialMediaSource | None,
    ) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.source = source
        self.page_title: str | None = None
        self.published_year: int | None = None
        self._meta_title: str | None = None
        self._og_image: str | None = None
        self._capture_h1 = False
        self._h1_parts: list[str] = []
        self._in_figure = False
        self._capture_caption = False
        self._caption_parts: list[str] = []
        self._figure_url: tuple[str, int] | None = None
        self._figure_alt: str | None = None
        self._figure_scope = 0
        self._article_depth = 0
        self._main_depth = 0
        self._ignored_depth = 0
        self.items: list[
            tuple[str, str | None, str | None, int, int]
        ] = []

    def _scope(self) -> int:
        if self._article_depth > 0:
            return 2
        if self._main_depth > 0:
            return 1
        return 0

    def _append(
        self,
        image_url: str,
        caption: str | None,
        alt_text: str | None,
        *,
        scope: int,
        score: int,
    ) -> None:
        if self._ignored_depth:
            return
        if not _source_allows_image(self.source, image_url):
            return
        self.items.append((image_url, caption, alt_text, scope, score))

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {key.casefold(): value for key, value in attrs if value is not None}
        lower = tag.casefold()

        if lower == "article":
            self._article_depth += 1
        elif lower == "main":
            self._main_depth += 1
        elif lower in {"nav", "footer", "aside"}:
            self._ignored_depth += 1

        if lower == "meta":
            key = (values.get("property") or values.get("name") or "").casefold()
            content = values.get("content")
            if key == "og:title" and content:
                self._meta_title = content.strip()
            elif key in {"og:image", "twitter:image"} and content and self._og_image is None:
                candidate = _normalize_image_url(content, base_url=self.page_url)
                if (
                    _source_allows_image(self.source, candidate)
                    and not _low_value_image(candidate)
                ):
                    self._og_image = candidate
            if content and (
                "published" in key
                or key in {"date", "datepublished", "article:published_time"}
            ):
                self.published_year = self.published_year or _published_year(content)
            return

        if lower == "time" and values.get("datetime"):
            self.published_year = self.published_year or _published_year(
                values["datetime"]
            )

        if lower == "h1" and self.page_title is None:
            self._capture_h1 = True
            self._h1_parts = []
            return

        if lower == "figure":
            self._in_figure = True
            self._figure_url = None
            self._figure_alt = None
            self._figure_scope = self._scope()
            self._caption_parts = []
            return

        if lower == "figcaption" and self._in_figure:
            self._capture_caption = True
            self._caption_parts = []
            return

        if self._ignored_depth:
            return

        if lower == "a" and self._in_figure:
            candidate = _image_href(
                values.get("href"),
                base_url=self.page_url,
                source=self.source,
            )
            if candidate and not _low_value_image(candidate):
                self._figure_url = (candidate, 20_000)
            return

        if lower == "source" and self._in_figure:
            candidates = _srcset_candidates(
                values.get("srcset") or values.get("data-srcset"),
                base_url=self.page_url,
                source=self.source,
            )
            candidates = [
                item
                for item in candidates
                if not _low_value_image(item[0], width_hint=item[1])
            ]
            if candidates:
                best = max(candidates, key=lambda item: item[1])
                if self._figure_url is None or best[1] > self._figure_url[1]:
                    self._figure_url = best
            return

        if lower != "img":
            return
        candidate = _best_img_candidate(
            values,
            base_url=self.page_url,
            source=self.source,
        )
        if candidate is None:
            return
        image_url, score = candidate
        alt = values.get("alt")
        if self._in_figure:
            if self._figure_url is None or score > self._figure_url[1]:
                self._figure_url = candidate
            if alt:
                self._figure_alt = alt
        elif alt or score >= 900:
            self._append(
                image_url,
                alt,
                alt,
                scope=self._scope(),
                score=score,
            )

    def handle_data(self, data: str) -> None:
        if self._capture_h1:
            self._h1_parts.append(data)
        if self._capture_caption:
            self._caption_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        lower = tag.casefold()
        if lower == "h1" and self._capture_h1:
            self._capture_h1 = False
            value = " ".join("".join(self._h1_parts).split())
            if value:
                self.page_title = value
        elif lower == "figcaption" and self._capture_caption:
            self._capture_caption = False
        elif lower == "figure" and self._in_figure:
            caption = " ".join("".join(self._caption_parts).split()) or None
            if self._figure_url is not None:
                self._append(
                    self._figure_url[0],
                    caption or self._figure_alt,
                    self._figure_alt,
                    scope=self._figure_scope,
                    score=self._figure_url[1],
                )
            self._in_figure = False
            self._figure_url = None
            self._figure_alt = None
            self._figure_scope = 0
            self._caption_parts = []

        if lower == "article" and self._article_depth:
            self._article_depth -= 1
        elif lower == "main" and self._main_depth:
            self._main_depth -= 1
        elif lower in {"nav", "footer", "aside"} and self._ignored_depth:
            self._ignored_depth -= 1


def parse_official_media_page(
    html_text: str,
    *,
    page_url: str,
    source: OfficialMediaSource | None = None,
) -> list[OfficialMediaItem]:
    parser = _PageMediaParser(page_url, source)
    parser.feed(html_text)
    parser.close()
    page_title = parser.page_title or parser._meta_title

    scoped_items = parser.items
    if any(item[3] == 2 for item in scoped_items):
        scoped_items = [item for item in scoped_items if item[3] == 2]
    elif any(item[3] == 1 for item in scoped_items):
        scoped_items = [item for item in scoped_items if item[3] == 1]

    if parser._og_image and not scoped_items:
        scoped_items.append(
            (
                parser._og_image,
                page_title,
                page_title,
                0,
                50_000,
            )
        )

    by_family: dict[
        str,
        tuple[str, str | None, str | None, int, int],
    ] = {}
    for item in scoped_items:
        image_url, caption, alt_text, scope, score = item
        effective_caption = caption or alt_text or page_title
        if not _caption_matches_page_event(
            source=source,
            page_title=page_title,
            caption=effective_caption,
        ):
            continue
        family = _asset_family_key(image_url, source=source)
        existing = by_family.get(family)
        rank = (
            scope,
            _asset_variant_rank(image_url, source=source),
            score,
        )
        if existing is not None:
            existing_rank = (
                existing[3],
                _asset_variant_rank(existing[0], source=source),
                existing[4],
            )
            if rank <= existing_rank:
                continue
        by_family[family] = item

    page_event = _event_key(page_title)
    season = parser.published_year or (page_event[0] if page_event else None)

    output: list[OfficialMediaItem] = []
    for image_url, caption, alt_text, _scope, _score in by_family.values():
        effective_caption = caption or alt_text or page_title
        photographer, agency, origin_provider = _credit_metadata(effective_caption)
        output.append(
            OfficialMediaItem(
                image_url=image_url,
                page_url=page_url,
                page_title=page_title,
                caption=effective_caption,
                alt_text=alt_text,
                content_role=infer_content_role(effective_caption),
                photographer=photographer,
                agency=agency,
                origin_provider=origin_provider,
                season=season,
            )
        )
    return output

