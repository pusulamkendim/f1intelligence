from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TemporalRelation = Literal[
    "occurred_at",
    "reported_at",
    "scheduled_for",
    "effective_from",
    "applies_to",
]
TimelinePrecision = Literal["season", "race", "session", "segment", "stint", "lap", "timestamp"]


class TimelineCoordinate(BaseModel):
    season: int
    race_id: str | None = None
    race_key: str | None = None
    race_label: str | None = None
    session_id: str | None = None
    session_code: str | None = None
    session_label: str | None = None
    segment_id: str | None = None
    segment_code: str | None = None
    segment_label: str | None = None
    driver_id: str | None = None
    driver_key: str | None = None
    driver_label: str | None = None
    stint_number: int | None = None
    lap_number: int | None = None


class TimelineProvenance(BaseModel):
    provider: str | None = None
    source_url: str | None = None
    fetched_at: datetime | None = None


class TimelineItem(BaseModel):
    id: str
    type: str
    label: str
    timeline_at: datetime | None = None
    reported_at: datetime | None = None
    temporal_relation: TemporalRelation
    precision: TimelinePrecision
    coordinate: TimelineCoordinate
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: TimelineProvenance | None = None


class UnifiedTimelineResponse(BaseModel):
    season: int
    race_key: str | None = None
    session_code: str | None = None
    driver_key: str | None = None
    lap_number: int | None = None
    items: list[TimelineItem] = Field(default_factory=list)
