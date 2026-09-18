from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class MediaObjectRef:
    bucket: str
    key: str
    public_url: str | None = None


class MediaStorageBackend(Protocol):
    async def store(
        self,
        *,
        asset_id: UUID,
        content: bytes,
        extension: str,
        public: bool,
    ) -> MediaObjectRef: ...


def media_object_key(
    *,
    season: int | None,
    race_slug: str | None,
    asset_id: UUID,
    variant: str,
    extension: str,
) -> str:
    clean_extension = extension.lower().lstrip(".")
    race_segment = race_slug or "unscoped"
    season_segment = str(season) if season is not None else "unknown-season"
    filename = f"{variant}.{clean_extension}"
    return str(
        PurePosixPath(
            season_segment,
            race_segment,
            "assets",
            str(asset_id),
            filename,
        )
    )


def planned_r2_original_key(
    *,
    season: int | None,
    race_slug: str | None,
    asset_id: UUID,
    extension: str,
) -> str:
    return media_object_key(
        season=season,
        race_slug=race_slug,
        asset_id=asset_id,
        variant="original",
        extension=extension,
    )
