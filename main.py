#!/usr/bin/env python3
"""
Simple main script for creating Superset charts.
"""

import sys
from auth import SupersetAuth
from chart_creator import SupersetChartCreator
from chart_configs import (
    SUPERSET_CONFIG, 
    DATASET_ID, 
    DASHBOARD_TITLE,
    CHARTS_CONFIG,
    BIG_NUMBER_CHARTS,
    LINE_CHARTS,
    SIMPLE_LINE,
    BAR_CHARTS,
    BUBBLE_CHARTS,
    TEST_BIG_NUMBER,
    TEST_LINE,
    TEST_BAR,
    TEST_BUBBLE,
    validate_all_configs
)

def main():
    try:
        # Authenticate
        print("🔐 Authenticating...")
        auth = SupersetAuth(
            superset_url=SUPERSET_CONFIG["url"],
            username=SUPERSET_CONFIG["username"], 
            password=SUPERSET_CONFIG["password"]
        )
        session, headers = auth.authenticate()
        print("✅ Authentication successful")
        
        # Initialize chart creator
        chart_creator = SupersetChartCreator(auth)
        
        # Test dataset
        if not chart_creator.test_dataset_query(DATASET_ID):
            print("❌ Dataset test failed. Check your DATASET_ID.")
            return
        
        # Choose chart type
        print("\n📊 Choose chart type to create:")
        print("1. Big Number Charts (recommended)")
        print("2. Simple Line Charts")
        print("3. Bar Charts")
        print("4. Bubble Charts")
        print("5. All Charts")
        print("6. Test Single Chart")
        print("7. Copy Working Chart")
        print("8. Analyze Working Chart Config")
        
        choice = input("\nEnter choice (1-8): ").strip() or "1"
        
        # Select charts
        if choice == "1":
            selected_charts = BIG_NUMBER_CHARTS
        elif choice == "2":
            selected_charts = SIMPLE_LINE
        elif choice == "3":
            selected_charts = BAR_CHARTS
        elif choice == "4":
            selected_charts = BUBBLE_CHARTS
        elif choice == "5":
            selected_charts = CHARTS_CONFIG
        elif choice == "6":
            selected_charts = TEST_BIG_NUMBER
        elif choice == "7":
            # Copy working chart
            chart_name = input("Enter the name of working chart to copy: ").strip()
            if not chart_name:
                chart_name = "Basic Line v1"
            new_name = input("Enter new chart name: ").strip()
            if not new_name:
                new_name = "copied line chart"
            
            chart_id = chart_creator.copy_working_chart(chart_name, new_name)
            if chart_id:
                print(f"✅ Successfully copied chart (ID: {chart_id})")
            else:
                print("❌ Failed to copy chart")
            return
        elif choice == "8":
            # Analyze working chart config
            chart_name = input("Enter chart name to analyze: ").strip()
            if not chart_name:
                chart_name = "Basic Line v1"
            
            analyze_working_chart(chart_creator, chart_name)
            return
        else:
            selected_charts = BIG_NUMBER_CHARTS
        
        print(f"\n🚀 Creating {len(selected_charts)} charts...")
        
        # Validate
        if not validate_all_configs(selected_charts):
            print("❌ Configuration validation failed")
            return
        
        # Create charts
        processed_charts = chart_creator.process_charts(
            charts_config=selected_charts,
            dataset_id=DATASET_ID,
            dashboard_title=DASHBOARD_TITLE
        )
        
        # Results
        print(f"\n✅ Created {len(processed_charts)} charts")
        if processed_charts:
            print(f"Chart IDs: {processed_charts}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def analyze_working_chart(chart_creator, chart_name):
    """Analyze and extract configuration from working chart"""
    print(f"\n🔍 Analyzing chart: {chart_name}")
    
    # Find the chart
    resp = chart_creator.session.get(f"{chart_creator.superset_url}/api/v1/chart/", headers=chart_creator.headers)
    if resp.status_code != 200:
        print(f"❌ Failed to list charts: {resp.status_code}")
        return
    
    charts = resp.json()["result"]
    chart_id = None
    for chart in charts:
        if chart["slice_name"] == chart_name:
            chart_id = chart["id"]
            break
    
    if not chart_id:
        print(f"❌ Chart '{chart_name}' not found")
        print("Available charts:")
        for chart in charts[:10]:  # Show first 10
            print(f"   - {chart['slice_name']}")
        return
    
    # Get chart config
    resp = chart_creator.session.get(f"{chart_creator.superset_url}/api/v1/chart/{chart_id}", headers=chart_creator.headers)
    if resp.status_code != 200:
        print(f"❌ Failed to get chart config: {resp.status_code}")
        return
    
    chart_data = resp.json()["result"]
    
    print(f"\n📊 CHART ANALYSIS: {chart_name}")
    print(f"Chart ID: {chart_id}")
    print(f"Viz Type: {chart_data['viz_type']}")
    
    # Extract and display params
    import json
    try:
        params = json.loads(chart_data.get('params', '{}'))
        print(f"\n📋 PARAMS:")
        for key, value in params.items():
            print(f"   {key}: {value}")
        
        print(f"\n🔧 CONFIG FOR COPYING:")
        print(f"viz_type: {chart_data['viz_type']}")
        if 'metric' in params:
            print(f"metric: {params['metric']}")
        if 'metrics' in params:
            print(f"metrics: {params['metrics']}")
        if 'groupby' in params:
            print(f"groupby: {params['groupby']}")
        if 'granularity_sqla' in params:
            print(f"granularity_sqla: {params['granularity_sqla']}")
        if 'time_grain_sqla' in params:
            print(f"time_grain_sqla: {params['time_grain_sqla']}")
            
        print(f"\n💡 SUGGESTED CONFIG:")
        print(f"{{")
        print(f'    "name": "New Line Chart",')
        print(f'    "viz_type": "{chart_data["viz_type"]}",')
        if 'metric' in params:
            print(f'    "metric": "{params["metric"]}",')
        elif 'metrics' in params and params['metrics']:
            print(f'    "metric": "{params["metrics"][0]}",')
        print(f'    "custom_params": {{')
        for key, value in params.items():
            if key not in ['datasource', 'viz_type', 'slice_name', 'metric', 'metrics']:
                if isinstance(value, str):
                    print(f'        "{key}": "{value}",')
                else:
                    print(f'        "{key}": {value},')
        print(f'    }}')
        print(f'}}')
        
    except Exception as e:
        print(f"❌ Error parsing params: {e}")
        print(f"Raw params: {chart_data.get('params', 'None')}")

def copy_basic_line_v1():
    """Copy the Basic Line v1 chart"""
    auth = SupersetAuth(SUPERSET_CONFIG["url"], SUPERSET_CONFIG["username"], SUPERSET_CONFIG["password"])
    auth.authenticate()
    chart_creator = SupersetChartCreator(auth)
    
    return chart_creator.copy_working_chart("Basic Line v1", "API Line Chart")

def test_big_number():
    """Quick test function"""
    auth = SupersetAuth(SUPERSET_CONFIG["url"], SUPERSET_CONFIG["username"], SUPERSET_CONFIG["password"])
    auth.authenticate()
    chart_creator = SupersetChartCreator(auth)
    
    return chart_creator.process_charts(
        charts_config=TEST_BIG_NUMBER,
        dataset_id=DATASET_ID,
        dashboard_title=None
    )

if __name__ == "__main__":
    main()