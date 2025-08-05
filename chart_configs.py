# === SIMPLE CHART CONFIGURATION FILE ===

# Superset connection settings
SUPERSET_CONFIG = {
    "url": "http://localhost:8088",
    "username": "admin",
    "password": "admin"
}

# Dataset and dashboard settings
DATASET_ID = 1
DASHBOARD_TITLE = "Analytics Dashboard"
UPDATE_MODE = True

# === CHART CONFIGURATIONS ===

# Big Number Charts (known to work)
BIG_NUMBER_CHARTS = [
    {
        "name": "Total Records",
        "viz_type": "big_number_total",
        "metric": "count"
    }
]

# Line Charts - Time Series like the screenshot
LINE_CHARTS = [
    {
        "name": "NPS Score Trend",
        "viz_type": "echarts_timeseries",
        "metric": "nps_score",  # Will become SUM(nps_score)
        "custom_params": {
            "show_markers": False,
            "line_interpolation": "linear"
        }
    }
]

# Simple Line Charts - try different approaches
SIMPLE_LINE = [
    {
        "name": "NPS Trend",
        "viz_type": "line",
        "metric_col": "nps_score",
        "metric": "SUM"
    },
    {
        "name": "Average CSAT",
        "viz_type": "line", 
        "metric_col": "csat_score",
        "metric": "AVG"
    },
    {
        "name": "Count Records",
        "viz_type": "line",
        "metric_col": "csat_score",  # Any column for COUNT
        "metric": "COUNT"
    }
]

# Bar Charts
BAR_CHARTS = [
    {
        "name": "Records by Category",
        "viz_type": "dist_bar",
        "metric": "count",
        "groupby_type": "category"
    }
]

# Bubble Charts
BUBBLE_CHARTS = [
    {
        "name": "Value Analysis",
        "viz_type": "bubble",
        "metric": "count",
        "custom_params": {
            "x": "column1",  # Replace with actual column name
            "y": "column2",  # Replace with actual column name
            "size": "count"
        }
    }
]

# Default charts to create
CHARTS_CONFIG = BIG_NUMBER_CHARTS + SIMPLE_LINE + BAR_CHARTS

# Test configurations
TEST_BIG_NUMBER = [{"name": "Test Big Number", "viz_type": "big_number_total", "metric": "count"}]
TEST_LINE = [{"name": "Test Time Series", "viz_type": "echarts_timeseries", "metric": "nps_score"}]
TEST_BAR = [{"name": "Test Bar", "viz_type": "dist_bar", "metric": "count", "groupby_type": "category"}]
TEST_BUBBLE = [{"name": "Test Bubble", "viz_type": "bubble", "metric": "count", "custom_params": {"x": "col1", "y": "col2", "size": "count"}}]

def validate_all_configs(charts_config):
    """Simple validation"""
    for config in charts_config:
        if "name" not in config or "viz_type" not in config:
            print(f"❌ Invalid config: {config}")
            return False
    return True