from typing import Any, Literal

from pydantic import BaseModel, Field

ChartType = Literal["line", "timeline"]


class VisualizationSeries(BaseModel):
    key: str
    label: str
    unit: str | None = None
    team_key: str | None = None
    team_label: str | None = None
    color: str | None = None
    points: list[dict[str, Any]] = Field(default_factory=list)


class VisualizationAnnotation(BaseModel):
    id: str
    type: str
    label: str
    lap: int | None = None
    occurred_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisualizationProvenance(BaseModel):
    provider: str
    source_url: str | None = None
    fetched_at: str | None = None
    datasets: list[str] = Field(default_factory=list)


class VisualizationResponse(BaseModel):
    key: str
    chart_type: ChartType
    title: str
    x_axis: str
    y_axis: str
    series: list[VisualizationSeries]
    annotations: list[VisualizationAnnotation] = Field(default_factory=list)
    provenance: list[VisualizationProvenance] = Field(default_factory=list)
