# === MAIN CONFIGURATION FILE ===
# This is the primary file you'll modify when creating different charts

# Superset connection settings
SUPERSET_CONFIG = {
    "url": "http://localhost:8088",
    "username": "admin",
    "password": "admin"
}

# Dataset and dashboard settings
DATASET_ID = 1  # Your dataset ID
DASHBOARD_ID = 1  # Set to specific dashboard ID to use existing dashboard, or None to create new
DASHBOARD_TITLE = "Auto Generated Dashboard"

# Operation mode settings
UPDATE_MODE = True  # If True, updates existing charts instead of creating duplicates
AUTO_UPDATE_DASHBOARD = True  # If True, automatically adds charts to dashboard

# === CHART CONFIGURATIONS ===
# Add, remove, or modify charts here
CHARTS_CONFIG = [
    {
        "name": "Record Count Over Time",
        "viz_type": "line",
        "metric": "COUNT",
        "groupby_type": "date"
    },
    {
        "name": "Data Distribution",
        "viz_type": "bar", 
        "metric": "COUNT",
        "groupby_type": "category"
    },
    {
        "name": "Total Records",
        "viz_type": "big_number_total",
        "metric": "COUNT",
        "groupby_type": None
    },
    {
        "name": "Data Breakdown",
        "viz_type": "pie",
        "metric": "COUNT",
        "groupby_type": "category"
    },
    # Add more chart configurations here as needed
    # {
    #     "name": "Custom Chart Name",
    #     "viz_type": "table",  # or any other supported viz type
    #     "metric": "COUNT",
    #     "groupby_type": "category"  # or "date" or None
    # },
]

# === ADVANCED CHART CONFIGURATIONS ===
# You can also define more complex chart configurations here

ADVANCED_CHARTS = [
    # Example of a more complex chart configuration
    # {
    #     "name": "Advanced Time Series",
    #     "viz_type": "line",
    #     "custom_params": {
    #         "show_markers": True,
    #         "line_interpolation": "cardinal"
    #     }
    # }
]

# Chart type reference for easy modification:
"""
Common viz_types:
- line: Line chart
- bar: Bar chart  
- pie: Pie chart
- table: Table view
- big_number_total: Big number display
- area: Area chart
- scatter: Scatter plot
- histogram: Histogram
- box_plot: Box plot
- heatmap: Heat map
- treemap: Tree map
- sankey: Sankey diagram
- gauge: Gauge chart
- bullet: Bullet chart
"""