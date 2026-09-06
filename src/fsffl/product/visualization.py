from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from fsffl.state.models import FrozenModel


class ChartKind(StrEnum):
    BAR = "bar"
    LINE = "line"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    STACKED_BAR = "stacked_bar"


class ChartDataPoint(FrozenModel):
    key: str
    label: str
    x: float | str | None = None
    y: float | None = None
    secondary_y: float | None = None
    group: str | None = None
    drilldown_ref: str | None = None

    @model_validator(mode="after")
    def validate_point(self) -> "ChartDataPoint":
        if not self.key.strip() or not self.label.strip():
            raise ValueError("chart point key/label cannot be blank")
        return self


class ChartSeries(FrozenModel):
    series_id: str
    label: str
    points: tuple[ChartDataPoint, ...]
    unit: str | None = None

    @model_validator(mode="after")
    def validate_series(self) -> "ChartSeries":
        if not self.series_id.strip() or not self.label.strip():
            raise ValueError("chart series identifiers cannot be blank")
        keys = [point.key for point in self.points]
        if len(keys) != len(set(keys)):
            raise ValueError("chart point keys must be unique within a series")
        return self


class InteractiveChartSpec(FrozenModel):
    chart_id: str
    kind: ChartKind
    title: str
    description: str = ""
    x_label: str | None = None
    y_label: str | None = None
    series: tuple[ChartSeries, ...]
    source_view: str
    source_model_versions: tuple[str, ...] = ()
    allow_drilldown: bool = True
    product_version: str = "next8-chart-v1"

    @model_validator(mode="after")
    def validate_chart(self) -> "InteractiveChartSpec":
        if any(not value.strip() for value in (self.chart_id, self.title, self.source_view, self.product_version)):
            raise ValueError("chart identifiers/title/source cannot be blank")
        if not self.series:
            raise ValueError("interactive chart requires at least one series")
        return self


class HeatMapCell(FrozenModel):
    row_key: str
    row_label: str
    column_key: str
    column_label: str
    value: float | None
    display_value: str | None = None
    drilldown_ref: str | None = None


class HeatMapSpec(FrozenModel):
    heatmap_id: str
    title: str
    cells: tuple[HeatMapCell, ...]
    metric_name: str
    source_view: str
    source_model_versions: tuple[str, ...] = ()
    product_version: str = "next8-heatmap-v1"

    @model_validator(mode="after")
    def validate_heatmap(self) -> "HeatMapSpec":
        if any(not value.strip() for value in (
            self.heatmap_id,
            self.title,
            self.metric_name,
            self.source_view,
            self.product_version,
        )):
            raise ValueError("heatmap identifiers/title/metric/source cannot be blank")
        keys = [(cell.row_key, cell.column_key) for cell in self.cells]
        if len(keys) != len(set(keys)):
            raise ValueError("heatmap cells must have unique row/column keys")
        return self
