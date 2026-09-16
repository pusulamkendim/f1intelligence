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


class StorySummary(BaseModel):
    id: UUID
    slug: str
    title: str
    summary: str | None = None
    status: str
    updated_at: datetime
    evidence_count: int
    latest_evidence_at: datetime | None = None


class StoryDetail(BaseModel):
    id: UUID
    slug: str
    title: str
    summary: str | None = None
    status: str
    significance: int
    confidence: str
    what_changed: str | None = None
    why_it_matters: str | None = None
    what_to_watch_next: str | None = None
    created_at: datetime
    updated_at: datetime
    evidence: list[EvidenceItem]
