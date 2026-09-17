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


class ContextResponse(BaseModel):
    contract_version: str = "1"
    target: ContextTarget
    relations: list[ContextRelation] = Field(default_factory=list)
    facets: list[ContextFacet] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
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
