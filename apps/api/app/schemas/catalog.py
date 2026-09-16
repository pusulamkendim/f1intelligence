from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.story import StorySummary


class TeamSummary(BaseModel):
    id: UUID
    slug: str
    name: str
    active_season: int | None = None
    driver_count: int
    story_count: int


class TeamMember(BaseModel):
    id: UUID
    slug: str
    display_name: str
    role: str
    season: int
    car_number: int | None = None


class TeamDetail(BaseModel):
    id: UUID
    slug: str
    name: str
    active_season: int | None = None
    members: list[TeamMember]
    stories: list[StorySummary]


class RaceSummary(BaseModel):
    id: UUID
    season: int
    round: int | None = None
    slug: str
    official_name: str
    circuit: str | None = None
    country: str | None = None
    start_at: datetime | None = None
    weekend_start_date: date | None = None
    weekend_end_date: date | None = None
    status: str
    story_count: int


class RaceDocumentSummary(BaseModel):
    id: UUID
    document_number: int | None = None
    title: str
    document_type: str
    document_url: str
    published_at: datetime | None = None
    recalled: bool


class RaceDetail(RaceSummary):
    synthesis: str | None = None
    stories: list[StorySummary]
    documents: list[RaceDocumentSummary]
