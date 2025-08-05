import json
import re
import time
from auth import SupersetAuth

class SupersetDashboardManager:
    def __init__(self, auth_instance):
        self.auth = auth_instance
        self.session = auth_instance.session
        self.headers = auth_instance.headers
        self.superset_url = auth_instance.superset_url
    
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

    def _generate_unique_slug(self, title, existing_slugs):
        """Generate a unique slug for the dashboard"""
        # Generate base slug
        base_slug = title.lower().replace(" ", "-").replace("_", "-")
        # Remove any special characters that might cause issues
        base_slug = re.sub(r'[^a-z0-9\-]', '', base_slug)
        
        slug = base_slug
        counter = 1
        
        # Check if slug exists and make it unique
        while slug in existing_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug

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
        slug = self._generate_unique_slug(title, existing_slugs)
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
            timestamp_slug = f"{slug}-{int(time.time())}"
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

    def get_dashboard_info(self, dashboard_id):
        """Get detailed information about a specific dashboard"""
        resp = self.session.get(f"{self.superset_url}/api/v1/dashboard/{dashboard_id}", headers=self.headers)
        if resp.status_code == 200:
            return resp.json()["result"]
        else:
            print(f"❌ Failed to get dashboard info: {resp.status_code}")
            return None

    def get_dashboard_charts(self, dashboard_id):
        """Get all charts in a dashboard"""
        dashboard_data = self.get_dashboard_info(dashboard_id)
        if not dashboard_data:
            return []
        
        # Extract chart IDs from the dashboard's slices relationship
        if "slices" in dashboard_data:
            chart_ids = [slice_info["id"] for slice_info in dashboard_data["slices"]]
            return chart_ids
        return []

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

    def add_charts_to_dashboard(self, dashboard_id, chart_ids):
        """Add charts to dashboard using the correct API approach"""
        if not chart_ids:
            print("⚠️ No chart IDs provided for dashboard update")
            return False
            
        # Get current dashboard info
        dashboard_data = self.get_dashboard_info(dashboard_id)
        if not dashboard_data:
            return False
        
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

    def remove_charts_from_dashboard(self, dashboard_id, chart_ids):
        """Remove charts from a dashboard"""
        dashboard_data = self.get_dashboard_info(dashboard_id)
        if not dashboard_data:
            return False
        
        try:
            # Parse position metadata
            position_json = dashboard_data.get("position_json", "{}")
            if isinstance(position_json, str):
                position_json = json.loads(position_json) if position_json else {}
            
            # Remove charts from position_json
            keys_to_remove = []
            for key, value in position_json.items():
                if isinstance(value, dict) and "meta" in value:
                    chart_id = value["meta"].get("chartId")
                    if chart_id in chart_ids:
                        keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del position_json[key]
            
            # Update dashboard
            payload = {
                "dashboard_title": dashboard_data["dashboard_title"],
                "slug": dashboard_data.get("slug", ""),
                "published": dashboard_data.get("published", True),
                "json_metadata": dashboard_data.get("json_metadata", "{}"),
                "position_json": json.dumps(position_json)
            }
            
            resp = self.session.put(f"{self.superset_url}/api/v1/dashboard/{dashboard_id}", headers=self.headers, json=payload)
            if resp.status_code == 200:
                print(f"✅ Removed {len(chart_ids)} charts from dashboard")
                return True
            else:
                print(f"❌ Failed to remove charts: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error removing charts: {e}")
            return False

    def delete_dashboard(self, dashboard_id):
        """Delete a dashboard by ID"""
        resp = self.session.delete(f"{self.superset_url}/api/v1/dashboard/{dashboard_id}", headers=self.headers)
        if resp.status_code == 200:
            print(f"✅ Deleted dashboard ID: {dashboard_id}")
            return True
        else:
            print(f"❌ Failed to delete dashboard {dashboard_id}: {resp.status_code} - {resp.text}")
            return False

    def update_dashboard_metadata(self, dashboard_id, title=None, description=None, published=None):
        """Update dashboard metadata"""
        dashboard_data = self.get_dashboard_info(dashboard_id)
        if not dashboard_data:
            return False
        
        payload = {
            "dashboard_title": title or dashboard_data["dashboard_title"],
            "slug": dashboard_data.get("slug", ""),
            "published": published if published is not None else dashboard_data.get("published", True),
            "json_metadata": dashboard_data.get("json_metadata", "{}"),
            "position_json": dashboard_data.get("position_json", "{}")
        }
        
        if description is not None:
            json_metadata = json.loads(dashboard_data.get("json_metadata", "{}"))
            json_metadata["description"] = description
            payload["json_metadata"] = json.dumps(json_metadata)
        
        resp = self.session.put(f"{self.superset_url}/api/v1/dashboard/{dashboard_id}", headers=self.headers, json=payload)
        if resp.status_code == 200:
            print(f"✅ Updated dashboard metadata")
            return True
        else:
            print(f"❌ Failed to update dashboard: {resp.status_code} - {resp.text}")
            return False