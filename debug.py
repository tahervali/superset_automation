import json
from auth import SupersetAuth
from dashboard_manager import SupersetDashboardManager

class WorkingChartCopier:
    def __init__(self, auth_instance):
        self.auth = auth_instance
        self.session = auth_instance.session
        self.headers = auth_instance.headers
        self.superset_url = auth_instance.superset_url

    def find_chart_by_name(self, chart_name):
        """Find chart ID by name"""
        resp = self.session.get(f"{self.superset_url}/api/v1/chart/", headers=self.headers)
        if resp.status_code == 200:
            charts = resp.json()["result"]
            for chart in charts:
                if chart["slice_name"] == chart_name:
                    return chart["id"]
        print(f"❌ Chart '{chart_name}' not found")
        return None

    def get_chart_config(self, chart_id):
        """Get full configuration from existing chart"""
        print(f"📋 Getting configuration from chart ID: {chart_id}")
        
        resp = self.session.get(f"{self.superset_url}/api/v1/chart/{chart_id}", headers=self.headers)
        if resp.status_code != 200:
            print(f"❌ Failed to get chart config: {resp.status_code} - {resp.text}")
            return None
        
        chart_data = resp.json()["result"]
        
        print(f"✅ Found chart: {chart_data['slice_name']}")
        print(f"📊 Viz type: {chart_data['viz_type']}")
        
        # Extract dataset ID from params or query_context JSON strings
        dataset_id = None
        datasource_type = "table"
        
        # Try to parse params JSON string
        try:
            params_str = chart_data.get('params', '{}')
            params = json.loads(params_str) if isinstance(params_str, str) else params_str
            
            # Look for datasource in params
            if 'datasource' in params:
                datasource = params['datasource']
                if '__table' in str(datasource):
                    # Format like "1__table"
                    dataset_id = int(datasource.split('__')[0])
                    print(f"📊 Dataset ID from params: {dataset_id}")
                elif isinstance(datasource, dict) and 'id' in datasource:
                    dataset_id = datasource['id']
                    datasource_type = datasource.get('type', 'table')
        except (json.JSONDecodeError, ValueError, AttributeError) as e:
            print(f"⚠️ Could not parse params: {e}")
        
        # If not found in params, try query_context
        if dataset_id is None:
            try:
                query_context_str = chart_data.get('query_context', '{}')
                query_context = json.loads(query_context_str) if isinstance(query_context_str, str) else query_context_str
                
                # Look for datasource in query_context
                if 'datasource' in query_context:
                    datasource = query_context['datasource']
                    if isinstance(datasource, dict):
                        dataset_id = datasource.get('id')
                        datasource_type = datasource.get('type', 'table')
                        print(f"📊 Dataset ID from query_context: {dataset_id}")
            except (json.JSONDecodeError, ValueError, AttributeError) as e:
                print(f"⚠️ Could not parse query_context: {e}")
        
        if dataset_id is None:
            print("⚠️ Could not find dataset ID in chart data")
            print(f"🔍 Params: {chart_data.get('params', 'None')}")
            print(f"🔍 Query context: {chart_data.get('query_context', 'None')}")
        else:
            print(f"✅ Extracted dataset ID: {dataset_id}, type: {datasource_type}")
        
        return chart_data

    def copy_chart(self, source_chart_name, new_chart_name):
        """Copy a chart by finding it by name and creating identical copy"""
        
        # Find the source chart
        source_chart_id = self.find_chart_by_name(source_chart_name)
        if not source_chart_id:
            return None
        
        # Get the source chart configuration
        source_config = self.get_chart_config(source_chart_id)
        if not source_config:
            return None
        
        print(f"\n🔍 SOURCE CHART CONFIG:")
        print(f"Slice name: {source_config['slice_name']}")
        print(f"Viz type: {source_config['viz_type']}")
        
        # Extract dataset information from JSON strings
        dataset_id = None
        datasource_type = "table"
        
        # Parse params to get dataset ID
        try:
            params_str = source_config.get('params', '{}')
            params = json.loads(params_str) if isinstance(params_str, str) else params_str
            
            if 'datasource' in params:
                datasource = params['datasource']
                if '__table' in str(datasource):
                    dataset_id = int(datasource.split('__')[0])
                elif isinstance(datasource, dict) and 'id' in datasource:
                    dataset_id = datasource['id']
                    datasource_type = datasource.get('type', 'table')
        except (json.JSONDecodeError, ValueError, AttributeError):
            pass
        
        # Try query_context if params didn't work
        if dataset_id is None:
            try:
                query_context_str = source_config.get('query_context', '{}')
                query_context = json.loads(query_context_str) if isinstance(query_context_str, str) else query_context_str
                
                if 'datasource' in query_context and isinstance(query_context['datasource'], dict):
                    dataset_id = query_context['datasource'].get('id')
                    datasource_type = query_context['datasource'].get('type', 'table')
            except (json.JSONDecodeError, ValueError, AttributeError):
                pass
        
        if dataset_id is None:
            print("❌ Could not extract dataset ID from source chart")
            return None
        
        print(f"📊 Dataset ID: {dataset_id}")
        print(f"📊 Datasource type: {datasource_type}")
        
        # Get the essential fields
        params = source_config.get('params', '{}')
        query_context = source_config.get('query_context', '{}')
        
        print(f"Params: {params}")
        print(f"Query context: {query_context}")
        
        # Create payload for new chart - use the most minimal structure that works
        new_payload = {
            "slice_name": new_chart_name,
            "viz_type": source_config["viz_type"],
            "datasource_id": dataset_id,
            "datasource_type": datasource_type,
            "params": params,
            "query_context": query_context
        }
        
        print(f"\n📋 NEW CHART PAYLOAD:")
        print(json.dumps(new_payload, indent=2))
        
        # Create the new chart
        print(f"\n🔨 Creating new chart '{new_chart_name}'...")
        resp = self.session.post(f"{self.superset_url}/api/v1/chart/", headers=self.headers, json=new_payload)
        
        print(f"📡 Response status: {resp.status_code}")
        print(f"📡 Response text: {resp.text}")
        
        if resp.status_code == 201:
            new_chart_id = resp.json()["id"]
            print(f"✅ Successfully created chart '{new_chart_name}' (ID: {new_chart_id})")
            return new_chart_id
        else:
            print(f"❌ Failed to create chart: {resp.status_code}")
            try:
                error_details = resp.json()
                print(f"Error details: {json.dumps(error_details, indent=2)}")
            except:
                print("Could not parse error response")
            return None

    def copy_chart_by_id(self, source_chart_id, new_chart_name):
        """Copy a chart by ID directly"""
        
        # Get the source chart configuration
        source_config = self.get_chart_config(source_chart_id)
        if not source_config:
            return None
        
        print(f"\n🔍 SOURCE CHART CONFIG:")
        print(f"Slice name: {source_config['slice_name']}")
        print(f"Viz type: {source_config['viz_type']}")
        
        # Extract dataset information from JSON strings
        dataset_id = None
        datasource_type = "table"
        
        # Parse params to get dataset ID
        try:
            params_str = source_config.get('params', '{}')
            params = json.loads(params_str) if isinstance(params_str, str) else params_str
            
            if 'datasource' in params:
                datasource = params['datasource']
                if '__table' in str(datasource):
                    dataset_id = int(datasource.split('__')[0])
                elif isinstance(datasource, dict) and 'id' in datasource:
                    dataset_id = datasource['id']
                    datasource_type = datasource.get('type', 'table')
        except (json.JSONDecodeError, ValueError, AttributeError):
            pass
        
        # Try query_context if params didn't work
        if dataset_id is None:
            try:
                query_context_str = source_config.get('query_context', '{}')
                query_context = json.loads(query_context_str) if isinstance(query_context_str, str) else query_context_str
                
                if 'datasource' in query_context and isinstance(query_context['datasource'], dict):
                    dataset_id = query_context['datasource'].get('id')
                    datasource_type = query_context['datasource'].get('type', 'table')
            except (json.JSONDecodeError, ValueError, AttributeError):
                pass
        
        if dataset_id is None:
            print("❌ Could not extract dataset ID from source chart")
            return None
        
        print(f"📊 Dataset ID: {dataset_id}")
        print(f"📊 Datasource type: {datasource_type}")
        
        # Get the essential fields
        params = source_config.get('params', '{}')
        query_context = source_config.get('query_context', '{}')
        
        print(f"Params: {params}")
        print(f"Query context: {query_context}")
        
        # Create payload for new chart
        new_payload = {
            "slice_name": new_chart_name,
            "viz_type": source_config["viz_type"],
            "datasource_id": dataset_id,
            "datasource_type": datasource_type,
            "params": params,
            "query_context": query_context
        }
        
        print(f"\n📋 NEW CHART PAYLOAD:")
        print(json.dumps(new_payload, indent=2))
        
        # Create the new chart
        print(f"\n🔨 Creating new chart '{new_chart_name}'...")
        resp = self.session.post(f"{self.superset_url}/api/v1/chart/", headers=self.headers, json=new_payload)
        
        print(f"📡 Response status: {resp.status_code}")
        print(f"📡 Response text: {resp.text}")
        
        if resp.status_code == 201:
            new_chart_id = resp.json()["id"]
            print(f"✅ Successfully created chart '{new_chart_name}' (ID: {new_chart_id})")
            return new_chart_id
        else:
            print(f"❌ Failed to create chart: {resp.status_code}")
            try:
                error_details = resp.json()
                print(f"Error details: {json.dumps(error_details, indent=2)}")
            except:
                print("Could not parse error response")
            return None

    def debug_chart_structure(self, chart_id):
        """Debug method to explore chart structure"""
        print(f"🔍 DEBUGGING CHART STRUCTURE FOR ID: {chart_id}")
        
        resp = self.session.get(f"{self.superset_url}/api/v1/chart/{chart_id}", headers=self.headers)
        if resp.status_code != 200:
            print(f"❌ Failed to get chart: {resp.status_code}")
            return
        
        chart_data = resp.json()["result"]
        
        print(f"\n📊 COMPLETE CHART DATA STRUCTURE:")
        print(json.dumps(chart_data, indent=2))
        
        print(f"\n📋 KEY ANALYSIS:")
        print(f"- Slice name: {chart_data.get('slice_name', 'NOT FOUND')}")
        print(f"- Viz type: {chart_data.get('viz_type', 'NOT FOUND')}")
        print(f"- Available keys: {list(chart_data.keys())}")
        
        # Look for dataset-related fields
        dataset_fields = []
        for key, value in chart_data.items():
            if 'datasource' in key.lower() or 'dataset' in key.lower() or 'table' in key.lower():
                dataset_fields.append(f"{key}: {value}")
        
        if dataset_fields:
            print(f"- Dataset-related fields:")
            for field in dataset_fields:
                print(f"  * {field}")
        else:
            print(f"- No obvious dataset fields found")


# USAGE SCRIPT
if __name__ == "__main__":
    # Initialize
    auth = SupersetAuth("http://localhost:8088", "admin", "admin")
    auth.authenticate()
    
    copier = WorkingChartCopier(auth)
    
    # First, debug the chart structure to understand what we're working with
    print("🔍 DEBUGGING CHART STRUCTURE FIRST...")
    copier.debug_chart_structure(40)  # Use your working chart ID
    
    print("\n" + "="*60 + "\n")
    
    # Then attempt to copy
    print("🔨 ATTEMPTING TO COPY CHART...")
    new_chart_id = copier.copy_chart("manual chart", "copy chart")
    
    # Alternative: Copy by ID directly if you know it
    # new_chart_id = copier.copy_chart_by_id(40, "copy chart")
    
    if new_chart_id:
        print(f"\n🎉 SUCCESS! Created copy chart with ID: {new_chart_id}")
    else:
        print(f"\n💥 FAILED to create copy chart")