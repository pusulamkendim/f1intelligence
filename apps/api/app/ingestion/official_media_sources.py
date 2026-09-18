from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

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
        page_path_pattern=r"^/20\\d{2}-formula-one-.+",
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


def _srcset_candidates(value: str | None, *, base_url: str) -> list[tuple[str, int]]:
    if not value:
        return []
    output: list[tuple[str, int]] = []
    for part in value.split(","):
        bits = part.strip().split()
        if not bits:
            continue
        url = urljoin(base_url, bits[0])
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


def _image_href(value: str | None, *, base_url: str) -> str | None:
    if not value:
        return None
    absolute = urljoin(base_url, value)
    clean = urlparse(absolute).path.casefold()
    if not clean.endswith(IMAGE_EXTENSIONS):
        return None
    return absolute


def _best_img_candidate(
    attrs: dict[str, str],
    *,
    base_url: str,
) -> tuple[str, int] | None:
    candidates: list[tuple[str, int]] = []
    for key in ("srcset", "data-srcset", "data-lazy-srcset"):
        candidates.extend(_srcset_candidates(attrs.get(key), base_url=base_url))

    for key, score in (
        ("data-full-url", 10_000),
        ("data-original", 9_500),
        ("data-src", 100),
        ("data-lazy-src", 90),
        ("src", 10),
    ):
        value = attrs.get(key)
        if value:
            candidates.append((urljoin(base_url, value), score))

    candidates = [
        (url, width)
        for url, width in candidates
        if urlparse(url).scheme in {"http", "https"}
        and not _low_value_image(url, width_hint=width)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[1])


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
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.page_title: str | None = None
        self._meta_title: str | None = None
        self._og_image: str | None = None
        self._capture_h1 = False
        self._h1_parts: list[str] = []
        self._in_figure = False
        self._capture_caption = False
        self._caption_parts: list[str] = []
        self._figure_url: tuple[str, int] | None = None
        self._figure_alt: str | None = None
        self.items: list[tuple[str, str | None, str | None]] = []
        self._seen: set[str] = set()

    def _append(
        self,
        image_url: str,
        caption: str | None,
        alt_text: str | None,
    ) -> None:
        if image_url in self._seen:
            return
        self._seen.add(image_url)
        self.items.append((image_url, caption, alt_text))

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {key.casefold(): value for key, value in attrs if value is not None}
        lower = tag.casefold()

        if lower == "meta":
            key = (values.get("property") or values.get("name") or "").casefold()
            content = values.get("content")
            if key == "og:title" and content:
                self._meta_title = content.strip()
            elif key in {"og:image", "twitter:image"} and content and self._og_image is None:
                candidate = urljoin(self.page_url, content)
                if not _low_value_image(candidate):
                    self._og_image = candidate
            return

        if lower == "h1" and self.page_title is None:
            self._capture_h1 = True
            self._h1_parts = []
            return

        if lower == "figure":
            self._in_figure = True
            self._figure_url = None
            self._figure_alt = None
            self._caption_parts = []
            return

        if lower == "figcaption" and self._in_figure:
            self._capture_caption = True
            self._caption_parts = []
            return

        if lower == "a" and self._in_figure:
            candidate = _image_href(values.get("href"), base_url=self.page_url)
            if candidate and not _low_value_image(candidate):
                self._figure_url = (candidate, 20_000)
            return

        if lower == "source" and self._in_figure:
            candidates = _srcset_candidates(
                values.get("srcset") or values.get("data-srcset"),
                base_url=self.page_url,
            )
            candidates = [
                item for item in candidates
                if not _low_value_image(item[0], width_hint=item[1])
            ]
            if candidates:
                best = max(candidates, key=lambda item: item[1])
                if self._figure_url is None or best[1] > self._figure_url[1]:
                    self._figure_url = best
            return

        if lower != "img":
            return
        candidate = _best_img_candidate(values, base_url=self.page_url)
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
            self._append(image_url, alt, alt)

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
                self._append(self._figure_url[0], caption or self._figure_alt, self._figure_alt)
            self._in_figure = False
            self._figure_url = None
            self._figure_alt = None
            self._caption_parts = []


def parse_official_media_page(
    html_text: str,
    *,
    page_url: str,
) -> list[OfficialMediaItem]:
    parser = _PageMediaParser(page_url)
    parser.feed(html_text)
    parser.close()
    page_title = parser.page_title or parser._meta_title

    if parser._og_image and parser._og_image not in parser._seen:
        parser._append(parser._og_image, page_title, page_title)

    output: list[OfficialMediaItem] = []
    for image_url, caption, alt_text in parser.items:
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
            )
        )
    return output
