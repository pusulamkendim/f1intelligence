from typing import Any, Literal

from pydantic import BaseModel, Field

ChartType = Literal["line", "timeline", "bar", "event_stream", "timing_table", "multi_panel"]
AxisDirection = Literal["normal", "reversed"]
RenderPreset = Literal[
    "position-trace",
    "lap-times",
    "stint-strategy",
    "sector-timing",
    "speed-comparison",
    "gap-interval",
    "pit-stop",
    "weather",
    "overtakes",
    "starting-grid",
    "championship-standings",
    "driver-season-results",
    "race-classification",
    "qualifying-classification",
    "mini-sector-timing",
    "timing-tower",
    "session-classification",
]


class VisualizationAxis(BaseModel):
    key: str
    label: str
    unit: str | None = None
    direction: AxisDirection = "normal"
    min: float | None = None
    max: float | None = None
    formatter: str | None = None


class VisualizationColumn(BaseModel):
    key: str
    label: str
    formatter: str | None = None
    align: Literal["left", "center", "right"] = "right"
    status_key: str | None = None


class VisualizationPresentation(BaseModel):
    preset: RenderPreset
    theme: str = "f1-timing-dark"
    dense: bool = True
    dark_preferred: bool = True
    tabular_numbers: bool = True
    team_color_rail: bool = True
    driver_label_mode: Literal["acronym", "full"] = "acronym"
    show_legend: bool = True
    show_annotations: bool = True
    columns: list[VisualizationColumn] = Field(default_factory=list)
    semantic_tokens: dict[str, str] = Field(default_factory=dict)


class VisualizationSeries(BaseModel):
    key: str
    label: str
    unit: str | None = None
    driver_number: int | None = None
    driver_acronym: str | None = None
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
    semantic_token: str | None = None
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
    x_axis: VisualizationAxis
    y_axis: VisualizationAxis
    presentation: VisualizationPresentation
    series: list[VisualizationSeries]
    annotations: list[VisualizationAnnotation] = Field(default_factory=list)
    provenance: list[VisualizationProvenance] = Field(default_factory=list)
