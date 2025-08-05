# === FIXED CHART CONFIGURATIONS ===
# Generated from working Chart ID 33 configuration

# Superset connection settings
SUPERSET_CONFIG = {
    "url": "http://localhost:8088",
    "username": "admin",
    "password": "admin"
}

# Dataset and dashboard settings
DATASET_ID = 1
DASHBOARD_TITLE = "Qualtrics Analytics Dashboard"

# Operation mode settings
UPDATE_MODE = True
AUTO_UPDATE_DASHBOARD = True

# === WORKING METRIC DEFINITION ===
# This metric structure is proven to work
WORKING_COUNT_METRIC = {
    "expressionType": "SQL",
    "sqlExpression": "COUNT(*)",
    "label": "COUNT(*)",
    "hasCustomLabel": false
}

# === WORKING CHART CONFIGURATION ===
CHARTS_CONFIG = [
    {
        "name": "Total Records",
        "viz_type": "big_number_total",
        "metric": WORKING_COUNT_METRIC,
        "groupby_type": None,
        "custom_params": {
            "number_format": "SMART_NUMBER",
            "subheader": "",
            "y_axis_format": "SMART_NUMBER"
        }
    }
]

# === ALTERNATIVE CONFIGURATIONS ===
# If you need more charts, use these patterns:

# Simple string metric (if your dataset has predefined metrics)
SIMPLE_CHARTS_CONFIG = [
    {
        "name": "Total Records - Simple",
        "viz_type": "big_number_total", 
        "metric": "count",  # Use the existing "count" metric from your dataset
        "groupby_type": None,
        "custom_params": {}
    }
]

# Complex charts with grouping
GROUPED_CHARTS_CONFIG = [
    {
        "name": "Records by Date",
        "viz_type": "line",
        "metric": WORKING_COUNT_METRIC,
        "groupby_type": "date",
        "custom_params": {
            "show_markers": True,
            "line_interpolation": "linear"
        }
    },
    {
        "name": "Average NPS Score",
        "viz_type": "big_number_total",
        "metric": {
            "expressionType": "SQL",
            "sqlExpression": "AVG(nps_score)",
            "label": "Average NPS",
            "hasCustomLabel": True
        },
        "groupby_type": None,
        "custom_params": {
            "number_format": ".2f",
            "subheader": "Net Promoter Score"
        }
    }
]

# === USAGE INSTRUCTIONS ===
"""
To use this configuration:

1. Save this as your new chart_configs.py
2. Run: python3 main.py
3. Select option 2 to create charts and dashboard

The WORKING_COUNT_METRIC is extracted from Chart ID 33 which is proven to work.
You can create additional metrics using the same pattern.
"""
