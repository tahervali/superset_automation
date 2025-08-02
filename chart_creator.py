import json
from auth import SupersetAuth

class SupersetChartCreator:
    def __init__(self, auth_instance):
        self.auth = auth_instance
        self.session = auth_instance.session
        self.headers = auth_instance.headers
        self.superset_url = auth_instance.superset_url
        self._existing_charts = None
    
    def select_column(self, columns, kind="date"):
        """Smart column selection based on column names"""
        if kind == "date":
            for col in columns:
                if any(k in col.lower() for k in ["date", "time", "timestamp"]):
                    return col
        elif kind == "category":
            for col in columns:
                if not any(k in col.lower() for k in ["id", "amount", "count"]):
                    return col
        return None
    
    def create_chart(self, chart_config, dataset_id, dataset_info):
        """Create a single chart based on configuration"""
        viz_type = chart_config["viz_type"]
        groupby_col = None

        if chart_config["groupby_type"] == "date":
            groupby_col = self.select_column(dataset_info["columns"], kind="date")
        elif chart_config["groupby_type"] == "category":
            groupby_col = self.select_column(dataset_info["columns"], kind="category")

        metric_obj = {
            "expressionType": "SQL",
            "sqlExpression": "COUNT(*)",
            "label": "COUNT"
        }

        query_context = {
            "datasource": {"id": dataset_id, "type": "table"},
            "queries": [
                {
                    "metrics": [metric_obj],
                    "groupby": [groupby_col] if groupby_col else [],
                    "filters": [],
                    "time_range": "No filter",
                    "orderby": [["COUNT", False]]
                }
            ],
            "result_format": "json",
            "result_type": "full"
        }

        params = {
            "metrics": [metric_obj],
            "groupby": [groupby_col] if groupby_col else [],
            "time_range": "No filter",
            "show_legend": True,
            "rich_tooltip": True,
            "slice_name": chart_config["name"]
        }

        payload = {
            "slice_name": chart_config["name"],
            "viz_type": viz_type,
            "datasource_id": dataset_id,
            "datasource_type": "table",
            "params": json.dumps(params),
            "query_context": json.dumps(query_context)
        }

        resp = self.session.post(f"{self.superset_url}/api/v1/chart/", headers=self.headers, json=payload)
        if resp.status_code == 201:
            chart_id = resp.json()["id"]
            print(f"✅ Created chart {chart_config['name']} (ID: {chart_id})")
            return chart_id
        else:
            print(f"❌ Failed to create chart {chart_config['name']}: {resp.status_code} - {resp.text}")
            return None
    
    def get_existing_dashboards(self):
        """Get all existing dashboards"""
        resp = self.session.get(f"{self.superset_url}/api/v1/dashboard/", headers=self.headers)
        if resp.status_code == 200:
            dashboards = resp.json()["result"]
            dashboard_dict = {
                dashboard["dashboard_title"]: {
                    "id": dashboard["id"],
                    "slug": dashboard["slug"]
                } for dashboard in dashboards
            }
            
            # Debug: Show existing dashboards
            print(f"📋 Found {len(dashboard_dict)} existing dashboards:")
            for title, info in dashboard_dict.items():
                print(f"   - '{title}' (ID: {info['id']}, slug: '{info['slug']}')")
            
            return dashboard_dict
        else:
            print(f"❌ Failed to fetch existing dashboards: {resp.status_code}")
            return {}

    def create_dashboard(self, title="Auto Dashboard"):
        """Create a new dashboard or return existing one"""
        # Check if dashboard with this title already exists
        existing_dashboards = self.get_existing_dashboards()
        
        if title in existing_dashboards:
            dashboard_id = existing_dashboards[title]["id"]
            print(f"✅ Found existing dashboard '{title}' (ID: {dashboard_id})")
            return dashboard_id
        
        # Get all existing slugs to ensure uniqueness
        resp = self.session.get(f"{self.superset_url}/api/v1/dashboard/", headers=self.headers)
        existing_slugs = []
        if resp.status_code == 200:
            dashboards = resp.json()["result"]
            existing_slugs = [d["slug"] for d in dashboards if d.get("slug")]
        
        # Generate unique slug
        base_slug = title.lower().replace(" ", "-").replace("_", "-")
        # Remove any special characters that might cause issues
        import re
        base_slug = re.sub(r'[^a-z0-9\-]', '', base_slug)
        
        slug = base_slug
        counter = 1
        
        # Check if slug exists and make it unique
        while slug in existing_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        print(f"🔄 Creating dashboard with slug: '{slug}'")
        
        payload = {
            "dashboard_title": title,
            "slug": slug,
            "published": True
        }
        
        resp = self.session.post(f"{self.superset_url}/api/v1/dashboard/", headers=self.headers, json=payload)
        if resp.status_code == 201:
            dashboard_id = resp.json()["id"]
            print(f"✅ Created dashboard '{title}' (ID: {dashboard_id}, slug: {slug})")
            return dashboard_id
        else:
            print(f"❌ Failed to create dashboard: {resp.status_code} - {resp.text}")
            # Try with a timestamp-based slug as last resort
            import time
            timestamp_slug = f"{base_slug}-{int(time.time())}"
            print(f"🔄 Retrying with timestamp slug: '{timestamp_slug}'")
            
            payload["slug"] = timestamp_slug
            resp = self.session.post(f"{self.superset_url}/api/v1/dashboard/", headers=self.headers, json=payload)
            if resp.status_code == 201:
                dashboard_id = resp.json()["id"]
                print(f"✅ Created dashboard '{title}' (ID: {dashboard_id}, slug: {timestamp_slug})")
                return dashboard_id
            else:
                print(f"❌ Still failed to create dashboard: {resp.status_code} - {resp.text}")
                return None
    
    def get_existing_charts(self, dataset_id=None):
        """Get all existing charts, optionally filtered by dataset"""
        if self._existing_charts is None:
            resp = self.session.get(f"{self.superset_url}/api/v1/chart/", headers=self.headers)
            if resp.status_code == 200:
                charts = resp.json()["result"]
                self._existing_charts = {
                    chart["slice_name"]: {
                        "id": chart["id"],
                        "datasource_id": chart["datasource_id"]
                    } for chart in charts
                }
            else:
                print(f"❌ Failed to fetch existing charts: {resp.status_code}")
                self._existing_charts = {}
        
        if dataset_id:
            return {name: info for name, info in self._existing_charts.items() 
                   if info["datasource_id"] == dataset_id}
        return self._existing_charts
    
    def update_chart(self, chart_id, chart_config, dataset_id, dataset_info):
        """Update an existing chart"""
        viz_type = chart_config["viz_type"]
        groupby_col = None

        if chart_config["groupby_type"] == "date":
            groupby_col = self.select_column(dataset_info["columns"], kind="date")
        elif chart_config["groupby_type"] == "category":
            groupby_col = self.select_column(dataset_info["columns"], kind="category")

        metric_obj = {
            "expressionType": "SQL",
            "sqlExpression": "COUNT(*)",
            "label": "COUNT"
        }

        query_context = {
            "datasource": {"id": dataset_id, "type": "table"},
            "queries": [
                {
                    "metrics": [metric_obj],
                    "groupby": [groupby_col] if groupby_col else [],
                    "filters": [],
                    "time_range": "No filter",
                    "orderby": [["COUNT", False]]
                }
            ],
            "result_format": "json",
            "result_type": "full"
        }

        params = {
            "metrics": [metric_obj],
            "groupby": [groupby_col] if groupby_col else [],
            "time_range": "No filter",
            "show_legend": True,
            "rich_tooltip": True,
            "slice_name": chart_config["name"]
        }

        payload = {
            "slice_name": chart_config["name"],
            "viz_type": viz_type,
            "datasource_id": dataset_id,
            "datasource_type": "table",
            "params": json.dumps(params),
            "query_context": json.dumps(query_context)
        }

        resp = self.session.put(f"{self.superset_url}/api/v1/chart/{chart_id}", headers=self.headers, json=payload)
        if resp.status_code == 200:
            print(f"✅ Updated chart {chart_config['name']} (ID: {chart_id})")
            return chart_id
        else:
            print(f"❌ Failed to update chart {chart_config['name']}: {resp.status_code} - {resp.text}")
            return None

    def create_or_update_chart(self, chart_config, dataset_id, dataset_info, existing_charts):
        """Create a new chart or update existing one based on name"""
        chart_name = chart_config["name"]
        
        if chart_name in existing_charts:
            chart_id = existing_charts[chart_name]["id"]
            print(f"🔄 Chart '{chart_name}' exists, updating...")
            return self.update_chart(chart_id, chart_config, dataset_id, dataset_info)
        else:
            print(f"➕ Creating new chart '{chart_name}'...")
            return self.create_chart(chart_config, dataset_id, dataset_info)

    def get_dashboard_charts(self, dashboard_id):
        """Get all charts in a dashboard"""
        resp = self.session.get(f"{self.superset_url}/api/v1/dashboard/{dashboard_id}", headers=self.headers)
        if resp.status_code == 200:
            dashboard_data = resp.json()["result"]
            # Extract chart IDs from the dashboard's JSON metadata
            charts = []
            if "json_metadata" in dashboard_data and dashboard_data["json_metadata"]:
                try:
                    metadata = json.loads(dashboard_data["json_metadata"])
                    charts = metadata.get("native_filter_configuration", [])
                except:
                    pass
            
            # Also get from slices relationship
            if "slices" in dashboard_data:
                chart_ids = [slice_info["id"] for slice_info in dashboard_data["slices"]]
                return chart_ids
            return []
        return []

    def update_dashboard_charts(self, dashboard_id, chart_ids):
        """Add charts to dashboard using the correct API approach"""
        if not chart_ids:
            print("⚠️ No chart IDs provided for dashboard update")
            return False
            
        # Get current dashboard info
        resp = self.session.get(f"{self.superset_url}/api/v1/dashboard/{dashboard_id}", headers=self.headers)
        if resp.status_code != 200:
            print(f"❌ Failed to get dashboard info: {resp.status_code}")
            return False
        
        dashboard_data = resp.json()["result"]
        current_chart_ids = [slice_info["id"] for slice_info in dashboard_data.get("slices", [])]
        
        # Filter out charts that are already in the dashboard
        new_chart_ids = [cid for cid in chart_ids if cid not in current_chart_ids]
        
        if not new_chart_ids:
            print("✅ All charts are already in the dashboard")
            return True
        
        # Method 1: Try the dashboard export/import approach
        success = self._add_charts_to_dashboard_v1(dashboard_id, new_chart_ids, dashboard_data)
        
        if not success:
            # Method 2: Try individual chart updates
            print("🔄 Trying alternative method...")
            success = self._add_charts_to_dashboard_v2(dashboard_id, new_chart_ids)
        
        return success
    
    def _add_charts_to_dashboard_v1(self, dashboard_id, chart_ids, dashboard_data):
        """Method 1: Update dashboard directly with position metadata"""
        try:
            # Parse existing JSON metadata
            json_metadata = dashboard_data.get("json_metadata", "{}")
            if isinstance(json_metadata, str):
                json_metadata = json.loads(json_metadata) if json_metadata else {}
            
            # Get current position metadata
            position_json = dashboard_data.get("position_json", "{}")
            if isinstance(position_json, str):
                position_json = json.loads(position_json) if position_json else {}
            
            # Add new charts to position (simple grid layout)
            next_row = 0
            for key, value in position_json.items():
                if isinstance(value, dict) and "meta" in value and value["meta"].get("chartId"):
                    next_row = max(next_row, value.get("y", 0) + value.get("h", 4))
            
            # Add new charts to position_json
            for i, chart_id in enumerate(chart_ids):
                chart_key = f"CHART-{chart_id}"
                position_json[chart_key] = {
                    "children": [],
                    "id": chart_key,
                    "meta": {
                        "chartId": chart_id,
                        "height": 50,
                        "sliceName": f"Chart {chart_id}",
                        "width": 4
                    },
                    "type": "CHART",
                    "x": (i % 3) * 4,  # 3 charts per row
                    "y": next_row + (i // 3) * 6,
                    "w": 4,
                    "h": 6
                }
            
            # Update dashboard
            payload = {
                "dashboard_title": dashboard_data["dashboard_title"],
                "slug": dashboard_data.get("slug", ""),
                "published": dashboard_data.get("published", True),
                "json_metadata": json.dumps(json_metadata),
                "position_json": json.dumps(position_json)
            }
            
            resp = self.session.put(f"{self.superset_url}/api/v1/dashboard/{dashboard_id}", headers=self.headers, json=payload)
            if resp.status_code == 200:
                print(f"✅ Added {len(chart_ids)} charts to dashboard using direct update")
                return True
            else:
                print(f"⚠️ Direct dashboard update failed: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"⚠️ Direct dashboard update failed: {e}")
            return False
    
    def _add_charts_to_dashboard_v2(self, dashboard_id, chart_ids):
        """Method 2: Use dashboard favorite/relationship endpoints"""
        success_count = 0
        
        for chart_id in chart_ids:
            try:
                # Try using the dashboard relationship endpoint
                payload = {"dashboard_ids": [dashboard_id]}
                resp = self.session.put(
                    f"{self.superset_url}/api/v1/chart/{chart_id}/dashboards", 
                    headers=self.headers, 
                    json=payload
                )
                
                if resp.status_code in [200, 201]:
                    success_count += 1
                    print(f"✅ Added chart {chart_id} to dashboard")
                else:
                    # Try alternative endpoint
                    resp2 = self.session.post(
                        f"{self.superset_url}/api/v1/dashboard/{dashboard_id}/charts",
                        headers=self.headers,
                        json={"chart_id": chart_id}
                    )
                    
                    if resp2.status_code in [200, 201]:
                        success_count += 1
                        print(f"✅ Added chart {chart_id} to dashboard (alt method)")
                    else:
                        print(f"⚠️ Failed to add chart {chart_id}: {resp.status_code} - {resp.text}")
            
            except Exception as e:
                print(f"⚠️ Error adding chart {chart_id}: {e}")
        
        if success_count > 0:
            print(f"✅ Successfully added {success_count} charts to dashboard")
            return True
        else:
            print("❌ Could not add charts to dashboard automatically")
            print(f"💡 Please manually add charts {chart_ids} to dashboard {dashboard_id}")
            return False

    def create_multiple_charts(self, charts_config, dataset_id, dashboard_id=None, update_mode=True):
        """Create or update multiple charts from configuration list"""
        dataset_info = self.auth.get_dataset_info(dataset_id)
        if not dataset_info:
            print("❌ No dataset info. Cannot create charts.")
            return []
        
        # Get existing charts for this dataset
        existing_charts = self.get_existing_charts(dataset_id) if update_mode else {}
        
        processed_charts = []
        for chart_config in charts_config:
            if update_mode:
                chart_id = self.create_or_update_chart(chart_config, dataset_id, dataset_info, existing_charts)
            else:
                chart_id = self.create_chart(chart_config, dataset_id, dataset_info)
            
            if chart_id:
                processed_charts.append(chart_id)
        
        # Update dashboard if provided
        if dashboard_id and processed_charts:
            print(f"\n🔄 Updating dashboard {dashboard_id} with charts...")
            self.update_dashboard_charts(dashboard_id, processed_charts)
        
        return processed_charts