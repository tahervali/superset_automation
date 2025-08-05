#!/usr/bin/env python3
"""
Proper fix for big_number_total charts based on the UI screenshot analysis.
The issue is that the chart is created but has an empty/invalid query.
"""

import json
from auth import SupersetAuth
from chart_configs import SUPERSET_CONFIG, DATASET_ID

def analyze_working_chart():
    """Analyze a working chart to understand the correct payload structure"""
    print("🔍 ANALYZING WORKING CHART STRUCTURE")
    print("=" * 45)
    
    try:
        auth = SupersetAuth(
            superset_url=SUPERSET_CONFIG["url"],
            username=SUPERSET_CONFIG["username"], 
            password=SUPERSET_CONFIG["password"]
        )
        
        session, headers = auth.authenticate()
        
        # Get all existing charts
        resp = session.get(f"{SUPERSET_CONFIG['url']}/api/v1/chart/", headers=headers)
        if resp.status_code != 200:
            print("❌ Could not fetch charts")
            return None
        
        charts = resp.json()["result"]
        
        # Look for any working big_number charts
        for chart in charts:
            if 'big_number' in chart.get('viz_type', ''):
                print(f"🔍 Found big number chart: {chart['slice_name']} (ID: {chart['id']})")
                
                # Get detailed chart info
                detail_resp = session.get(f"{SUPERSET_CONFIG['url']}/api/v1/chart/{chart['id']}", headers=headers)
                if detail_resp.status_code == 200:
                    chart_detail = detail_resp.json()["result"]
                    print(f"📊 Chart details:")
                    print(f"   - Viz type: {chart_detail['viz_type']}")
                    print(f"   - Params: {chart_detail['params']}")
                    print(f"   - Query context: {chart_detail.get('query_context', 'None')}")
                    return chart_detail
        
        print("📊 No existing big_number charts found")
        return None
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return None

def create_chart_like_ui():
    """Create a chart using the exact same structure as the Superset UI would"""
    print("\n🎯 CREATING CHART LIKE SUPERSET UI")
    print("=" * 40)
    
    try:
        auth = SupersetAuth(
            superset_url=SUPERSET_CONFIG["url"],
            username=SUPERSET_CONFIG["username"], 
            password=SUPERSET_CONFIG["password"]
        )
        
        session, headers = auth.authenticate()
        
        # Get dataset info to understand the structure
        dataset_info = auth.get_dataset_info(DATASET_ID)
        if not dataset_info:
            print("❌ Could not get dataset info")
            return None
        
        print(f"📊 Dataset columns: {dataset_info['columns']}")
        print(f"📊 Dataset metrics: {dataset_info['metrics']}")
        
        # Check if COUNT(*) metric exists in dataset
        available_metrics = dataset_info.get('metrics', [])
        
        # Try different metric approaches
        metric_approaches = [
            # Approach 1: Use existing COUNT metric if available
            {
                "name": "Total Records - Existing Metric",
                "metric": available_metrics[0] if available_metrics else "COUNT(*)"
            },
            
            # Approach 2: Use the actual COUNT(*) function name from dataset
            {
                "name": "Total Records - COUNT Function", 
                "metric": "COUNT(*)"
            },
            
            # Approach 3: Use metric object that matches UI structure
            {
                "name": "Total Records - Metric Object",
                "metric": {
                    "aggregate": "COUNT",
                    "column": None,
                    "expressionType": "SIMPLE",
                    "hasCustomLabel": False,
                    "label": "COUNT(*)",
                    "sqlExpression": None
                }
            },
            
            # Approach 4: Use adhoc metric (common in newer Superset versions)
            {
                "name": "Total Records - Adhoc Metric",
                "metric": {
                    "expressionType": "SQL",
                    "sqlExpression": "COUNT(*)",
                    "label": "COUNT(*)",
                    "hasCustomLabel": False
                }
            }
        ]
        
        successful_charts = []
        
        for approach in metric_approaches:
            print(f"\n🧪 Testing: {approach['name']}")
            
            # Build payload structure that matches UI expectations
            if isinstance(approach['metric'], dict):
                metrics = [approach['metric']]
            else:
                metrics = [approach['metric']]
            
            # Build comprehensive params like UI would
            params = {
                "datasource": f"{DATASET_ID}__table",
                "viz_type": "big_number_total",
                "slice_id": None,
                "url_params": {},
                "granularity_sqla": None,
                "time_grain_sqla": "P1D",
                "time_range": "No filter",
                "metrics": metrics,
                "adhoc_filters": [],
                "groupby": [],
                "columns": [],
                "row_limit": 10000,
                "limit": 0,
                "timeseries_limit_metric": None,
                "order_desc": True,
                "contribution": False,
                "number_format": "SMART_NUMBER",
                "force_categorical": False,
                "subheader": "",
                "y_axis_format": "SMART_NUMBER"
            }
            
            payload = {
                "slice_name": approach['name'],
                "viz_type": "big_number_total",
                "datasource_id": DATASET_ID,
                "datasource_type": "table",
                "params": json.dumps(params),
                "description": "",
                "cache_timeout": None,
                "owners": []
            }
            
            print(f"📤 Sending payload...")
            print(f"   Metrics: {metrics}")
            
            resp = session.post(f"{SUPERSET_CONFIG['url']}/api/v1/chart/", headers=headers, json=payload)
            
            if resp.status_code == 201:
                chart_id = resp.json()["id"]
                print(f"✅ Chart created with ID: {chart_id}")
                
                # Test if the chart actually works by running its query
                print(f"🔍 Testing chart execution...")
                
                # Get the created chart details
                chart_resp = session.get(f"{SUPERSET_CONFIG['url']}/api/v1/chart/{chart_id}", headers=headers)
                if chart_resp.status_code == 200:
                    chart_data = chart_resp.json()["result"]
                    
                    # Try to execute the chart query
                    query_payload = {
                        "datasource": {"id": DATASET_ID, "type": "table"},
                        "queries": [{
                            "metrics": metrics,
                            "groupby": [],
                            "filters": [],
                            "row_limit": 1
                        }]
                    }
                    
                    query_resp = session.post(
                        f"{SUPERSET_CONFIG['url']}/api/v1/chart/data",
                        headers=headers,
                        json={"query_context": json.dumps(query_payload)}
                    )
                    
                    if query_resp.status_code == 200:
                        print(f"✅ Chart query executes successfully!")
                        successful_charts.append((approach['name'], chart_id))
                    else:
                        print(f"❌ Chart query failed: {query_resp.status_code} - {query_resp.text}")
                else:
                    print(f"⚠️ Could not verify chart execution")
                    
            else:
                print(f"❌ Chart creation failed: {resp.status_code} - {resp.text}")
        
        print(f"\n📊 RESULTS:")
        print(f"✅ {len(successful_charts)} working charts created")
        
        for name, chart_id in successful_charts:
            print(f"   - {name} (ID: {chart_id})")
            print(f"     URL: {SUPERSET_CONFIG['url']}/superset/explore/?form_data_key=...&slice_id={chart_id}")
        
        return successful_charts
        
    except Exception as e:
        print(f"❌ Chart creation failed: {e}")
        import traceback
        traceback.print_exc()
        return []

def inspect_dataset_metrics():
    """Inspect what metrics are actually available in the dataset"""
    print("\n🔍 INSPECTING DATASET METRICS")
    print("=" * 35)
    
    try:
        auth = SupersetAuth(
            superset_url=SUPERSET_CONFIG["url"],
            username=SUPERSET_CONFIG["username"], 
            password=SUPERSET_CONFIG["password"]
        )
        
        session, headers = auth.authenticate()
        
        # Get detailed dataset info
        resp = session.get(f"{SUPERSET_CONFIG['url']}/api/v1/dataset/{DATASET_ID}", headers=headers)
        if resp.status_code != 200:
            print(f"❌ Could not get dataset details: {resp.status_code}")
            return
        
        dataset = resp.json()["result"]
        
        print(f"📊 Dataset: {dataset.get('table_name', 'Unknown')}")
        print(f"📊 Schema: {dataset.get('schema', 'Unknown')}")
        
        # Check columns
        columns = dataset.get('columns', [])
        print(f"\n📋 Columns ({len(columns)}):")
        for col in columns[:10]:  # Show first 10
            print(f"   - {col['column_name']} ({col['type']})")
        
        # Check metrics  
        metrics = dataset.get('metrics', [])
        print(f"\n📈 Metrics ({len(metrics)}):")
        for metric in metrics:
            print(f"   - {metric['metric_name']}: {metric.get('expression', 'No expression')}")
        
        if not metrics:
            print("⚠️ No predefined metrics found in dataset!")
            print("💡 This might be why COUNT(*) isn't working - you may need to create metrics first")
        
        return dataset
        
    except Exception as e:
        print(f"❌ Dataset inspection failed: {e}")
        return None

def create_count_metric_in_dataset():
    """Create a COUNT(*) metric in the dataset if it doesn't exist"""
    print("\n➕ CREATING COUNT METRIC IN DATASET")
    print("=" * 40)
    
    try:
        auth = SupersetAuth(
            superset_url=SUPERSET_CONFIG["url"],
            username=SUPERSET_CONFIG["username"], 
            password=SUPERSET_CONFIG["password"]
        )
        
        session, headers = auth.authenticate()
        
        # Create a metric in the dataset
        metric_payload = {
            "metric_name": "count_all_records",
            "expression": "COUNT(*)",
            "description": "Count of all records",
            "metric_type": "count",
            "verbose_name": "Total Records",
            "d3format": ",d"
        }
        
        resp = session.post(
            f"{SUPERSET_CONFIG['url']}/api/v1/dataset/{DATASET_ID}/metric",
            headers=headers,
            json=metric_payload
        )
        
        if resp.status_code == 201:
            metric_id = resp.json()["id"]
            print(f"✅ Created metric 'count_all_records' (ID: {metric_id})")
            return metric_id
        else:
            print(f"❌ Failed to create metric: {resp.status_code} - {resp.text}")
            return None
            
    except Exception as e:
        print(f"❌ Metric creation failed: {e}")
        return None

if __name__ == "__main__":
    print("🚀 COMPREHENSIVE BIG NUMBER CHART FIX")
    print("=" * 50)
    
    # Step 1: Analyze existing charts
    print("Step 1: Analyzing existing charts...")
    working_chart = analyze_working_chart()
    
    # Step 2: Inspect dataset metrics
    print("\nStep 2: Inspecting dataset...")
    dataset_info = inspect_dataset_metrics()
    
    # Step 3: Try to create a metric if none exist
    if dataset_info and not dataset_info.get('metrics'):
        print("\nStep 3: Creating COUNT metric in dataset...")
        metric_id = create_count_metric_in_dataset()
    
    # Step 4: Try different chart creation approaches
    print("\nStep 4: Testing chart creation approaches...")
    successful_charts = create_chart_like_ui()
    
    # Summary
    print(f"\n🏁 FINAL RESULTS:")
    if successful_charts:
        print(f"✅ {len(successful_charts)} working charts created!")
        print(f"🌐 Check these charts in your Superset UI")
    else:
        print(f"❌ No working charts created")
        print(f"💡 Next steps:")
        print(f"   1. Check if your dataset has proper permissions")
        print(f"   2. Try creating a chart manually in the UI first")
        print(f"   3. Check Superset server logs for detailed errors")