from __future__ import annotations

import re

# Keep the source-of-record title untouched. These patterns only produce the title
# used for entity/relation classification, so publisher chrome does not become a
# semantic subject merely because it is embedded in the document title.
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
    original = " ".join(title.split())
    cleaned = original
    for pattern in _TITLE_STRIP_PATTERNS.get(source_key, ()):
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip(" |–—-:")
    return cleaned or original
