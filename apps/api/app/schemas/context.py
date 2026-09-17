from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ContextTargetType = Literal["driver", "team", "race", "session", "season", "story"]


class ContextTarget(BaseModel):
    type: ContextTargetType
    id: str
    key: str
    slug: str | None = None
    label: str
    subtype: str | None = None
    season: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextTargetRef(BaseModel):
    type: str
    id: str
    key: str
    label: str
    subtype: str | None = None


class ContextRelation(BaseModel):
    type: str
    target: ContextTargetRef
    scope: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextFacet(BaseModel):
    type: str
    count: int
    status: Literal["available"] = "available"


class ContextProvenance(BaseModel):
    provider: str | None = None
    source_url: str | None = None
    fetched_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextTimelineEvent(BaseModel):
    id: str
    type: str
    # Legacy anchor name kept for contract compatibility. For scheduled/effective
    # events this is the timeline coordinate, not a claim that the event occurred.
    occurred_at: datetime
    temporal_relation: str = "occurred_at"
    reported_at: datetime | None = None
    precision: str | None = None
    label: str
    target: ContextTargetRef | None = None
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: ContextProvenance | None = None


class ContextResponse(BaseModel):
    contract_version: str = "1"
    target: ContextTarget
    relations: list[ContextRelation] = Field(default_factory=list)
    facets: list[ContextFacet] = Field(default_factory=list)
    timeline: list[ContextTimelineEvent] = Field(default_factory=list)
    related: list[ContextTargetRef] = Field(default_factory=list)
    provenance: list[ContextProvenance] = Field(default_factory=list)


class ContextFacetPage(BaseModel):
    target: ContextTarget
    facet: str
    total: int
    limit: int
    offset: int
    next_offset: int | None = None
    items: list[dict[str, Any]] = Field(default_factory=list)
