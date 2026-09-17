from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_PROMO_TAIL_RE = re.compile(
    r"\s*(?:[.;|–—-]+\s*)?(?:"
    r"keep reading.*|"
    r"read also:.*|"
    r"watch every session.*|"
    r"watch all sessions.*|"
    r"live on sky sports.*"
    r")$",
    re.IGNORECASE,
)


def clean_text(value: str | None) -> str | None:
    """Remove transport/HTML artefacts while preserving editorial wording."""
    if value is None:
        return None
    cleaned = value
    # Some feeds double-encode entities, so decode twice but never rewrite semantics.
    for _ in range(2):
        decoded = html.unescape(cleaned)
        if decoded == cleaned:
            break
        cleaned = decoded
    cleaned = _TAG_RE.sub(" ", cleaned)
    cleaned = cleaned.replace("\u00a0", " ")
    cleaned = _SPACE_RE.sub(" ", cleaned).strip()
    return cleaned or None


def clean_title(value: str) -> str:
    return clean_text(value) or "Untitled Formula 1 story"


def clean_summary(value: str | None) -> str | None:
    cleaned = clean_text(value)
    if cleaned is None:
        return None

    # Feed excerpts often append navigation/promotional boilerplate. Remove only
    # well-known trailing markers; source_items keep their provenance separately.
    previous = None
    while previous != cleaned:
        previous = cleaned
        cleaned = _PROMO_TAIL_RE.sub("", cleaned).strip()

    # Motorsport feeds can embed a Read Also block before the final CTA.
    marker = re.search(r"\bRead Also:\s*", cleaned, flags=re.IGNORECASE)
    if marker:
        cleaned = cleaned[: marker.start()].rstrip(" .;|–—-")

    return cleaned or None
