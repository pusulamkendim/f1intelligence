from __future__ import annotations

import re

from app.ingestion.content_cleanup import clean_title

# Keep source-specific chrome removal narrow. Transport artefacts such as HTML
# entities are decoded before classification, while publisher wording remains
# otherwise untouched unless explicitly configured here.
_TITLE_STRIP_PATTERNS: dict[str, tuple[str, ...]] = {
    "team_haas": (
        r"^Haas F1 Team\s*\|\s*",
    ),
    "team_racing_bulls": (
        r"\s*\|\s*VCARB\s*\|\s*Visa Cash App RB\s*$",
        r"\s*\|\s*Visa Cash App RB\s*$",
    ),
}


def classification_title(source_key: str, title: str) -> str:
    original = clean_title(title)
    cleaned = original
    for pattern in _TITLE_STRIP_PATTERNS.get(source_key, ()):
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip(" |–—-:")
    return cleaned or original
