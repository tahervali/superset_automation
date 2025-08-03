import json
from typing import Dict, Any, Optional

class ChartConfig:
    def __init__(self, title: str, x_axis: str, y_axis: str, chart_type: str, data_source: str, filters: Optional[Dict[str, Any]] = None):
        self.title = title
        self.x_axis = x_axis
        self.y_axis = y_axis
        self.chart_type = chart_type
        self.data_source = data_source
        self.filters = filters if filters is not None else {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "chart_type": self.chart_type,
            "data_source": self.data_source,
            "filters": self.filters
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @staticmethod
    def from_dict(config_dict: Dict[str, Any]) -> 'ChartConfig':
        return ChartConfig(
            title=config_dict.get("title", ""),
            x_axis=config_dict.get("x_axis", ""),
            y_axis=config_dict.get("y_axis", ""),
            chart_type=config_dict.get("chart_type", ""),
            data_source=config_dict.get("data_source", ""),
            filters=config_dict.get("filters", {})
        )

    @staticmethod
    def from_json(config_json: str) -> 'ChartConfig':
        config_dict = json.loads(config_json)
        return ChartConfig.from_dict(config_dict)
