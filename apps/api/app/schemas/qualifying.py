from typing import Literal

from pydantic import BaseModel

QualifyingSegmentCode = Literal["q1", "q2", "q3"]


class QualifyingSegmentDriverResult(BaseModel):
    driver_number: int
    driver_key: str | None = None
    driver_label: str | None = None
    team_key: str | None = None
    team_label: str | None = None
    segment_position: int | None = None
    final_qualifying_position: int | None = None
    duration_seconds: float | None = None
    gap_to_leader_seconds: float | None = None
    reached_next_segment: bool | None = None


class QualifyingSegmentResponse(BaseModel):
    race_key: str
    race_label: str
    session_id: str
    segment_id: str
    segment_code: QualifyingSegmentCode
    segment_label: str
    sequence: int
    provider: str
    source_url: str | None = None
    rows: list[QualifyingSegmentDriverResult]
