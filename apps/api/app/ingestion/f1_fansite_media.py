from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from app.ingestion.media_assets import infer_content_role

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".avif")


@dataclass(frozen=True)
class F1FansiteMediaItem:
    image_url: str
    gallery_url: str
    gallery_title: str | None
    caption: str | None
    alt_text: str | None
    content_role: str
    photographer: str | None
    agency: str | None
    origin_provider: str | None
    origin_asset_id: str | None
    rights_note: str | None


class _GalleryIndexParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.urls: list[str] = []
        self.seen: set[str] = set()

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
        absolute = urljoin(self.base_url, href)
        parsed = urlparse(absolute)
        if "f1-fansite.com" not in parsed.netloc.casefold():
            return
        if "/f1-wallpaper/" not in parsed.path:
            return
        canonical = f"https://www.f1-fansite.com{parsed.path.rstrip('/')}/"
        if canonical not in self.seen:
            self.seen.add(canonical)
            self.urls.append(canonical)


def discover_gallery_urls(html_text: str, *, base_url: str) -> list[str]:
    parser = _GalleryIndexParser(base_url)
    parser.feed(html_text)
    parser.close()
    return parser.urls


class _GalleryParser(HTMLParser):
    def __init__(self, gallery_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.gallery_url = gallery_url
        self.gallery_title: str | None = None
        self._capture_h1 = False
        self._h1_parts: list[str] = []
        self._in_figure = False
        self._capture_caption = False
        self._caption_parts: list[str] = []
        self._figure_href: str | None = None
        self._figure_src: str | None = None
        self._figure_alt: str | None = None
        self.items: list[tuple[str, str | None, str | None]] = []
        self._seen: set[str] = set()

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {key.casefold(): value for key, value in attrs if value is not None}
        lower = tag.casefold()
        if lower == "h1" and self.gallery_title is None:
            self._capture_h1 = True
            self._h1_parts = []
        elif lower == "figure":
            self._in_figure = True
            self._figure_href = None
            self._figure_src = None
            self._figure_alt = None
            self._caption_parts = []
        elif lower == "figcaption" and self._in_figure:
            self._capture_caption = True
            self._caption_parts = []
        elif lower == "a" and self._in_figure:
            href = values.get("href")
            if href and _looks_like_image(href):
                self._figure_href = urljoin(self.gallery_url, href)
        elif lower == "img":
            src = (
                values.get("data-full-url")
                or values.get("data-src")
                or values.get("data-lazy-src")
                or values.get("src")
            )
            if not src or not _looks_like_image(src):
                return
            absolute = urljoin(self.gallery_url, src)
            alt = values.get("alt")
            if self._in_figure:
                self._figure_src = absolute
                self._figure_alt = alt
            elif "wp-content/uploads" in absolute and absolute not in self._seen:
                self._seen.add(absolute)
                self.items.append((absolute, alt, alt))

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
                self.gallery_title = value
        elif lower == "figcaption" and self._capture_caption:
            self._capture_caption = False
        elif lower == "figure" and self._in_figure:
            image_url = self._figure_href or self._figure_src
            caption = " ".join("".join(self._caption_parts).split()) or None
            if image_url and image_url not in self._seen:
                self._seen.add(image_url)
                self.items.append((image_url, caption, self._figure_alt))
            self._in_figure = False


def _looks_like_image(url: str) -> bool:
    clean = url.lower().split("?", 1)[0]
    return clean.endswith(IMAGE_EXTENSIONS)


def _origin_metadata(
    caption: str | None,
) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    value = caption or ""
    photographer = None
    agency = None
    photo_match = re.search(
        r"\(?Photo(?:graph)? by\s+([^()/]+?)/([^()]+?)\)",
        value,
        flags=re.IGNORECASE,
    )
    if photo_match:
        photographer = " ".join(photo_match.group(1).split())
        agency = " ".join(photo_match.group(2).split())

    lower = value.casefold()
    if "red bull content pool" in lower:
        origin_provider = "red_bull_content_pool"
    elif "getty images" in lower:
        origin_provider = "getty_images"
    elif agency and "lat images" in agency.casefold():
        origin_provider = "lat_images"
    elif agency and "sutton" in agency.casefold():
        origin_provider = "sutton_images"
    elif agency and "dppi" in agency.casefold():
        origin_provider = "dppi"
    else:
        origin_provider = None

    asset_match = re.search(r"\b(SI\d{9,}|\d{10})\b", value)
    origin_asset_id = asset_match.group(1) if asset_match else None

    rights_note = None
    if "editorial use only" in lower:
        rights_note = "editorial use only"
    return photographer, agency, origin_provider, origin_asset_id, rights_note


def parse_gallery_html(
    html_text: str,
    *,
    gallery_url: str,
) -> list[F1FansiteMediaItem]:
    parser = _GalleryParser(gallery_url)
    parser.feed(html_text)
    parser.close()

    output: list[F1FansiteMediaItem] = []
    for image_url, caption, alt_text in parser.items:
        effective_caption = caption or alt_text
        (
            photographer,
            agency,
            origin_provider,
            origin_asset_id,
            rights_note,
        ) = _origin_metadata(effective_caption)
        output.append(
            F1FansiteMediaItem(
                image_url=image_url,
                gallery_url=gallery_url,
                gallery_title=parser.gallery_title,
                caption=effective_caption,
                alt_text=alt_text,
                content_role=infer_content_role(effective_caption),
                photographer=photographer,
                agency=agency,
                origin_provider=origin_provider,
                origin_asset_id=origin_asset_id,
                rights_note=rights_note,
            )
        )
    return output
