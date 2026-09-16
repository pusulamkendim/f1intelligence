from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IngestionEntity(BaseModel):
    id: UUID
    entity_type: str
    slug: str
    display_name: str
    matched_alias: str
    confidence: int


class IngestionQueueItem(BaseModel):
    id: UUID
    source_key: str
    source_name: str
    source_type: str
    external_id: str
    source_url: str | None = None
    title: str
    published_at: datetime | None = None
    status: str
    match_score: int | None = None
    ingested_at: datetime
    matched_story_slug: str | None = None
    matched_story_title: str | None = None
    entities: list[IngestionEntity]


class IngestionQueueCounts(BaseModel):
    attached: int = 0
    unmatched: int = 0
    ambiguous: int = 0
    filtered: int = 0


class IngestionQueue(BaseModel):
    counts: IngestionQueueCounts
    items: list[IngestionQueueItem]
