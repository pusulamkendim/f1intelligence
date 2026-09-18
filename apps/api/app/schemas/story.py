from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class EvidenceItem(BaseModel):
    id: UUID
    presentation_type: str
    source_type: str
    source_name: str
    source_url: str | None = None
    published_at: datetime | None = None
    captured_at: datetime
    author_or_speaker: str | None = None
    normalized_claim: str | None = None
    raw_excerpt_or_reference: str | None = None
    reliability_class: str | None = None
    directness: str | None = None
    metadata: dict[str, Any]


class StoryEntity(BaseModel):
    id: UUID
    entity_type: str
    slug: str
    display_name: str
    relation_type: str
    confidence: int
    match_method: str
    matched_alias: str | None = None


class StorySourceItem(BaseModel):
    source_item_id: UUID
    provider: str
    source_type: str
    source_class: str
    title: str
    source_url: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    relation_type: str
    cluster_method: str
    cluster_confidence: int


class StoryMediaCandidate(BaseModel):
    media_asset_id: UUID
    story_role: str
    content_role: str
    url: str
    caption: str | None = None
    source_provider: str
    origin_provider: str | None = None
    photographer: str | None = None
    agency: str | None = None
    rights_status: str
    storage_policy: str
    match_reason: str
    confidence: int
    selected: bool = False


class StorySummary(BaseModel):
    id: UUID
    slug: str
    title: str
    summary: str | None = None
    status: str
    taxonomy: str | None = None
    source_count: int = 0
    first_published_at: datetime | None = None
    last_published_at: datetime | None = None
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None
    updated_at: datetime
    evidence_count: int
    latest_evidence_at: datetime | None = None
    hero_media_asset_id: UUID | None = None
    hero_image_url: str | None = None


class StoryDetail(BaseModel):
    id: UUID
    slug: str
    title: str
    summary: str | None = None
    status: str
    taxonomy: str | None = None
    source_count: int = 0
    first_published_at: datetime | None = None
    last_published_at: datetime | None = None
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None
    significance: int
    confidence: str
    what_changed: str | None = None
    why_it_matters: str | None = None
    what_to_watch_next: str | None = None
    created_at: datetime
    updated_at: datetime
    entities: list[StoryEntity]
    sources: list[StorySourceItem]
    evidence: list[EvidenceItem]
    media: list[StoryMediaCandidate]
