import json
from auth import SupersetAuth
from dashboard_manager import SupersetDashboardManager

class SupersetChartCreator:
    def __init__(self, auth_instance):
        self.auth = auth_instance
        self.session = auth_instance.session
        self.headers = auth_instance.headers
        self.superset_url = auth_instance.superset_url
        self._existing_charts = None
        # Initialize dashboard manager
        self.dashboard_manager = SupersetDashboardManager(auth_instance)
    
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
        elif kind == "numeric":
            for col in columns:
                if any(k in col.lower() for k in ["amount", "value", "price", "score", "count", "number"]):
                    return col
        return None

    # === CHART TYPE SPECIFIC METHODS ===

    def _build_big_number_chart(self, chart_config, dataset_id, dataset_info):
        """Build payload specifically for big_number_total charts"""
        chart_name = chart_config["name"]
        metric = chart_config.get("metric", "count")
        
        # Big number specific form_data
        form_data = {
            "datasource": f"{dataset_id}__table",
            "viz_type": "big_number_total",
            "metric": metric,
            "adhoc_filters": [
                {
                    "clause": "WHERE",
                    "subject": "date" if self.select_column(dataset_info["columns"], "date") else None,
                    "operator": "TEMPORAL_RANGE",
                    "comparator": "No filter",
                    "expressionType": "SIMPLE"
                }
            ] if self.select_column(dataset_info["columns"], "date") else [],
            "header_font_size": chart_config.get("custom_params", {}).get("header_font_size", 0.4),
            "subheader_font_size": chart_config.get("custom_params", {}).get("subheader_font_size", 0.15),
            "y_axis_format": chart_config.get("custom_params", {}).get("y_axis_format", "SMART_NUMBER"),
            "time_format": chart_config.get("custom_params", {}).get("time_format", "smart_date"),
            "extra_form_data": {},
            "dashboards": []
        }
        
        # Add any additional custom params
        if "custom_params" in chart_config:
            for key, value in chart_config["custom_params"].items():
                if key not in form_data:  # Don't override existing keys
                    form_data[key] = value
        
        # Big number specific query_context
        query_context = {
            "datasource": {"id": dataset_id, "type": "table"},
            "force": False,
            "queries": [
                {
                    "filters": [
                        {
                            "col": self.select_column(dataset_info["columns"], "date") or "date",
                            "op": "TEMPORAL_RANGE",
                            "val": "No filter"
                        }
                    ] if self.select_column(dataset_info["columns"], "date") else [],
                    "extras": {"having": "", "where": ""},
                    "applied_time_extras": {},
                    "columns": [],
                    "metrics": [metric],
                    "annotation_layers": [],
                    "series_limit": 0,
                    "order_desc": True,
                    "url_params": {},
                    "custom_params": {},
                    "custom_form_data": {}
                }
            ],
            "form_data": form_data.copy(),
            "result_format": "json",
            "result_type": "full"
        }
        
        # Add required fields to form_data for query_context
        query_context["form_data"].update({
            "force": False,
            "result_format": "json",
            "result_type": "full"
        })
        
        return {
            "slice_name": chart_name,
            "viz_type": "big_number_total",
            "datasource_id": dataset_id,
            "datasource_type": "table",
            "params": json.dumps(form_data),
            "query_context": json.dumps(query_context)
        }

    def _build_line_chart(self, chart_config, dataset_id, dataset_info):
        """Build payload for basic line charts - FIXED for categorical X-axis"""
        chart_name = chart_config["name"]
        
        # Handle metric configuration
        raw_metric = chart_config.get("metric", "AVG(nps_score)")
        
        # Parse metric properly
        if "(" in raw_metric and ")" in raw_metric:
            agg_func = raw_metric.split("(")[0].strip().upper()
            column_part = raw_metric.split("(")[1].split(")")[0].strip()
            
            if column_part == "*":
                # COUNT(*) case
                adhoc_metric = {
                    "expressionType": "SQL",
                    "sqlExpression": "COUNT(*)",
                    "label": "COUNT(*)",
                    "hasCustomLabel": False,
                    "optionName": "metric_count_all"
                }
            else:
                # Regular aggregation like AVG(nps_score)
                adhoc_metric = {
                    "expressionType": "SQL",
                    "sqlExpression": f"{agg_func}({column_part})",
                    "label": f"{agg_func}({column_part})",
                    "hasCustomLabel": False,
                    "optionName": f"metric_{column_part}_{agg_func.lower()}"
                }
        else:
            # Fallback: treat as column name with AVG
            adhoc_metric = {
                "expressionType": "SQL",
                "sqlExpression": f"AVG({raw_metric})",
                "label": f"AVG({raw_metric})",
                "hasCustomLabel": False,
                "optionName": f"metric_{raw_metric}_avg"
            }
        
        # Handle X-axis configuration
        x_axis_config = chart_config.get("x_axis", "date")
        
        # Check if we need to extract day of week from date
        if x_axis_config == "day_of_week":
            # Use SQL to extract day of week from date column
            date_col = self.select_column(dataset_info["columns"], "date") or "date"
            
            # Create a custom column for day of week
            day_of_week_column = {
                "expressionType": "SQL",
                "sqlExpression": f"TO_CHAR({date_col}, 'Day')",  # PostgreSQL syntax
                "label": "Day of Week",
                "hasCustomLabel": True,
                "optionName": "day_of_week_custom"
            }
            
            groupby_columns = [day_of_week_column]
            is_temporal = False
            granularity_col = None
            
        elif x_axis_config == "month":
            # Extract month from date
            date_col = self.select_column(dataset_info["columns"], "date") or "date"
            
            month_column = {
                "expressionType": "SQL", 
                "sqlExpression": f"TO_CHAR({date_col}, 'Month')",  # PostgreSQL syntax
                "label": "Month",
                "hasCustomLabel": True,
                "optionName": "month_custom"
            }
            
            groupby_columns = [month_column]
            is_temporal = False
            granularity_col = None
            
        elif x_axis_config in dataset_info["columns"]:
            # Use existing column
            groupby_columns = [x_axis_config]
            is_temporal = False
            granularity_col = None
            
        else:
            # Default to time-series behavior
            is_temporal = True
            groupby_columns = []
            granularity_col = self.select_column(dataset_info["columns"], "date") or "date"
        
        # Build form_data
        form_data = {
            "datasource": f"{dataset_id}__table",
            "viz_type": "line",
            "slice_id": None,
            
            # Metrics
            "metrics": [adhoc_metric],
            "adhoc_filters": [],
            
            # Grouping configuration
            "groupby": groupby_columns if not is_temporal else [],
            "columns": [],
            
            # Time configuration (only for temporal charts)
            "granularity_sqla": granularity_col if is_temporal else None,
            "time_grain_sqla": "P1D" if is_temporal else None,
            "time_range": "No filter" if is_temporal else None,
            
            # Chart appearance
            "row_limit": chart_config.get("custom_params", {}).get("row_limit", 10000),
            "color_scheme": chart_config.get("custom_params", {}).get("color_scheme", "supersetColors"),
            "show_brush": "auto" if is_temporal else False,
            "send_time_range": is_temporal,
            "show_legend": chart_config.get("custom_params", {}).get("show_legend", True),
            "rich_tooltip": chart_config.get("custom_params", {}).get("rich_tooltip", True),
            "show_markers": chart_config.get("custom_params", {}).get("show_markers", True),
            "line_interpolation": chart_config.get("custom_params", {}).get("line_interpolation", "linear"),
            
            # Axis formatting
            "bottom_margin": "auto",
            "x_ticks_layout": "auto",
            "x_axis_format": "smart_date" if is_temporal else "",
            "left_margin": "auto",
            "y_axis_format": chart_config.get("custom_params", {}).get("y_axis_format", "SMART_NUMBER"),
            "y_axis_bounds": chart_config.get("custom_params", {}).get("y_axis_bounds", [None, None]),
            
            # Additional options
            "rolling_type": "None",
            "comparison_type": "values",
            "annotation_layers": [],
            "extra_form_data": {},
            "dashboards": []
        }
        
        # Remove None values to avoid issues
        form_data = {k: v for k, v in form_data.items() if v is not None}
        
        # Query context
        query_context = {
            "datasource": {"id": dataset_id, "type": "table"},
            "force": False,
            "queries": [
                {
                    "filters": [],
                    "extras": {"having": "", "where": ""},
                    "applied_time_extras": {},
                    "columns": groupby_columns if not is_temporal else [],
                    "metrics": [adhoc_metric],
                    "groupby": groupby_columns if not is_temporal else [],
                    "annotation_layers": [],
                    "row_limit": form_data["row_limit"],
                    "series_limit": 0,
                    "order_desc": False,  # Changed to False for better categorical ordering
                    "url_params": {},
                    "custom_params": {},
                    "custom_form_data": {}
                }
            ],
            "form_data": form_data.copy(),
            "result_format": "json",
            "result_type": "full"
        }
        
        # Add temporal fields only if needed
        if is_temporal:
            query_context["queries"][0]["time_range"] = "No filter"
            query_context["queries"][0]["granularity"] = granularity_col
            query_context["queries"][0]["extras"]["time_grain_sqla"] = "P1D"
        
        query_context["form_data"].update({
            "force": False,
            "result_format": "json",
            "result_type": "full"
        })
        
        return {
            "slice_name": chart_name,
            "viz_type": "line",
            "datasource_id": dataset_id,
            "datasource_type": "table",
            "params": json.dumps(form_data),
            "query_context": json.dumps(query_context)
        }

    def _build_bar_chart(self, chart_config, dataset_id, dataset_info):
        chart_name = chart_config["name"]
        metric_col = chart_config.get("metric", "nps_score")
        
        # Get date column
        date_col = self.select_column(dataset_info["columns"], "date") or "date"
        
        # Create SQL expression metric
        sql_metric = {
            "expressionType": "SQL",
            "sqlExpression": f"SUM({metric_col})",
            "label": f"SUM({metric_col})",
            "hasCustomLabel": False
        }
        
        form_data = {
            "datasource": f"{dataset_id}__table",
            "viz_type": "line",
            "granularity_sqla": date_col,
            "time_grain_sqla": "P1D",
            "time_range": "No filter",
            "metrics": [sql_metric],
            "adhoc_filters": [],
            "groupby": [],
            "row_limit": 10000,
            "color_scheme": "supersetColors",
            "show_brush": "auto",
            "send_time_range": False,
            "show_legend": True,
            "rich_tooltip": True,
            "show_markers": True,
            "line_interpolation": "linear",
            "bottom_margin": "auto",
            "x_ticks_layout": "auto",
            "x_axis_format": "smart_date",
            "left_margin": "auto",
            "y_axis_format": "SMART_NUMBER",
            "y_axis_bounds": [None, None],
            "rolling_type": "None",
            "comparison_type": "values",
            "annotation_layers": [],
            "extra_form_data": {},
            "dashboards": []
        }
        
        # Query context with SQL metric
        query_context = {
            "datasource": {"id": dataset_id, "type": "table"},
            "force": False,
            "queries": [
                {
                    "time_range": "No filter",
                    "granularity": date_col,
                    "filters": [],
                    "extras": {"time_grain_sqla": "P1D", "having": "", "where": ""},
                    "applied_time_extras": {},
                    "columns": [],
                    "metrics": [sql_metric],
                    "annotation_layers": [],
                    "row_limit": 10000,
                    "series_limit": 0,
                    "order_desc": True,
                    "url_params": {},
                    "custom_params": {},
                    "custom_form_data": {}
                }
            ],
            "form_data": form_data.copy(),
            "result_format": "json",
            "result_type": "full"
        }
        
        query_context["form_data"].update({
            "force": False,
            "result_format": "json",
            "result_type": "full"
        })
        
        return {
            "slice_name": chart_name,
            "viz_type": "line",
            "datasource_id": dataset_id,
            "datasource_type": "table",
            "params": json.dumps(form_data),
            "query_context": json.dumps(query_context)
        }

    def _build_bubble_chart(self, chart_config, dataset_id, dataset_info):
        """Build payload specifically for bubble charts"""
        chart_name = chart_config["name"]
        metric = chart_config.get("metric", "count")
        
        # Get x and y columns (numeric preferred)
        x_col = chart_config.get("custom_params", {}).get("x") or self.select_column(dataset_info["columns"], "numeric")
        y_col = chart_config.get("custom_params", {}).get("y") or self.select_column(dataset_info["columns"], "numeric")
        size_metric = chart_config.get("custom_params", {}).get("size", metric)
        
        # Series column for grouping bubbles
        series_col = chart_config.get("custom_params", {}).get("series") or self.select_column(dataset_info["columns"], "category")
        
        # Bubble chart specific form_data
        form_data = {
            "datasource": f"{dataset_id}__table",
            "viz_type": "bubble",
            "x": x_col,
            "y": y_col,
            "size": size_metric,
            "series": series_col,
            "entity": chart_config.get("custom_params", {}).get("entity", ""),
            "adhoc_filters": [],
            "time_range": "No filter",
            "row_limit": chart_config.get("custom_params", {}).get("row_limit", 100),
            "show_legend": chart_config.get("custom_params", {}).get("show_legend", True),
            "max_bubble_size": chart_config.get("custom_params", {}).get("max_bubble_size", 25),
            "color_scheme": chart_config.get("custom_params", {}).get("color_scheme", "supersetColors"),
            "extra_form_data": {},
            "dashboards": []
        }
        
        # Add any additional custom params
        if "custom_params" in chart_config:
            for key, value in chart_config["custom_params"].items():
                if key not in form_data:
                    form_data[key] = value
        
        # Bubble chart specific query_context
        query_context = {
            "datasource": {"id": dataset_id, "type": "table"},
            "force": False,
            "queries": [
                {
                    "filters": [],
                    "extras": {"having": "", "where": ""},
                    "applied_time_extras": {},
                    "columns": [col for col in [x_col, y_col, series_col] if col],
                    "metrics": [size_metric] if isinstance(size_metric, str) else [size_metric],
                    "groupby": [series_col] if series_col else [],
                    "annotation_layers": [],
                    "row_limit": form_data["row_limit"],
                    "series_limit": 0,
                    "order_desc": True,
                    "url_params": {},
                    "custom_params": {},
                    "custom_form_data": {}
                }
            ],
            "form_data": form_data.copy(),
            "result_format": "json",
            "result_type": "full"
        }
        
        query_context["form_data"].update({
            "force": False,
            "result_format": "json",
            "result_type": "full"
        })
        
        return {
            "slice_name": chart_name,
            "viz_type": "bubble",
            "datasource_id": dataset_id,
            "datasource_type": "table",
            "params": json.dumps(form_data),
            "query_context": json.dumps(query_context)
        }

    # === MAIN CHART BUILDING METHOD ===
    
    def _build_chart_payload(self, chart_config, dataset_id, dataset_info):
        """Route to specific chart building method based on viz_type"""
        viz_type = chart_config["viz_type"]
        
        print(f"🔧 Building {viz_type} chart: {chart_config['name']}")
        print("chart_config: ", chart_config)
        print(viz_type)
        # Route to specific method based on chart type
        if viz_type == "big_number_total":
            return self._build_big_number_chart(chart_config, dataset_id, dataset_info)
        elif viz_type == "line":
            return self._build_line_chart(chart_config, dataset_id, dataset_info)
        elif viz_type in ["dist_bar", "bar"]:
            return self._build_bar_chart(chart_config, dataset_id, dataset_info)
        elif viz_type == "bubble":
            return self._build_bubble_chart(chart_config, dataset_id, dataset_info)
        else:
            print(f"⚠️ Unsupported chart type: {viz_type}. Using generic method.")
            return self._build_generic_chart(chart_config, dataset_id, dataset_info)
    
    def _build_generic_chart(self, chart_config, dataset_id, dataset_info):
        """Fallback method for unsupported chart types"""
        chart_name = chart_config["name"]
        viz_type = chart_config["viz_type"]
        metric = chart_config.get("metric", "count")
        
        # Generic form_data
        form_data = {
            "datasource": f"{dataset_id}__table",
            "viz_type": viz_type,
            "slice_name": chart_name,
            "adhoc_filters": [],
            "time_range": "No filter",
            "dashboards": []
        }
        
        # Add metric
        if viz_type == "big_number_total":
            form_data["metric"] = metric
        else:
            form_data["metrics"] = [metric] if isinstance(metric, str) else metric
        
        # Add groupby if specified
        if chart_config.get("groupby_type"):
            if chart_config["groupby_type"] == "date":
                groupby_col = self.select_column(dataset_info["columns"], "date")
                if groupby_col:
                    form_data["groupby"] = [groupby_col]
            elif chart_config["groupby_type"] == "category":
                groupby_col = self.select_column(dataset_info["columns"], "category")
                if groupby_col:
                    form_data["groupby"] = [groupby_col]
        
        # Add custom params
        if "custom_params" in chart_config:
            form_data.update(chart_config["custom_params"])
        
        # Generic query_context
        query_context = {
            "datasource": {"id": dataset_id, "type": "table"},
            "force": False,
            "queries": [
                {
                    "filters": [],
                    "extras": {"having": "", "where": ""},
                    "applied_time_extras": {},
                    "columns": [],
                    "metrics": form_data.get("metrics", [form_data.get("metric", metric)]),
                    "groupby": form_data.get("groupby", []),
                    "annotation_layers": [],
                    "series_limit": 0,
                    "order_desc": True,
                    "url_params": {},
                    "custom_params": {},
                    "custom_form_data": {}
                }
            ],
            "form_data": form_data.copy(),
            "result_format": "json",
            "result_type": "full"
        }
        
        query_context["form_data"].update({
            "force": False,
            "result_format": "json",
            "result_type": "full"
        })
        
        return {
            "slice_name": chart_name,
            "viz_type": viz_type,
            "datasource_id": dataset_id,
            "datasource_type": "table",
            "params": json.dumps(form_data),
            "query_context": json.dumps(query_context)
        }

    # === EXISTING METHODS (unchanged) ===
    
    def create_chart(self, chart_config, dataset_id, dataset_info):
        """Create a single chart based on configuration"""
        payload = self._build_chart_payload(chart_config, dataset_id, dataset_info)
        print(f"[DEBUG] Chart payload for '{chart_config['name']}':\n{json.dumps(payload, indent=2)}")
        resp = self.session.post(f"{self.superset_url}/api/v1/chart/", headers=self.headers, json=payload)
        if resp.status_code == 201:
            chart_id = resp.json()["id"]
            print(f"✅ Created chart {chart_config['name']} (ID: {chart_id})")
            return chart_id
        else:
            print(f"❌ Failed to create chart {chart_config['name']}: {resp.status_code} - {resp.text}")
            return None
    
    def update_chart(self, chart_id, chart_config, dataset_id, dataset_info):
        """Update an existing chart"""
        payload = self._build_chart_payload(chart_config, dataset_id, dataset_info)
        print(f"[DEBUG] Chart payload for '{chart_config['name']}':\n{json.dumps(payload, indent=2)}")
        resp = self.session.put(f"{self.superset_url}/api/v1/chart/{chart_id}", headers=self.headers, json=payload)
        if resp.status_code == 200:
            print(f"✅ Updated chart {chart_config['name']} (ID: {chart_id})")
            return chart_id
        else:
            print(f"❌ Failed to update chart {chart_config['name']}: {resp.status_code} - {resp.text}")
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
                        "datasource_id": self._extract_dataset_id_from_chart(chart)
                    } for chart in charts
                }
            else:
                print(f"❌ Failed to fetch existing charts: {resp.status_code}")
                self._existing_charts = {}
        
        if dataset_id:
            return {name: info for name, info in self._existing_charts.items() 
                   if info["datasource_id"] == dataset_id}
        return self._existing_charts
    
    def _extract_dataset_id_from_chart(self, chart):
        """Extract dataset ID from chart object in listing"""
        if "datasource_id" in chart:
            return chart["datasource_id"]
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

    def create_multiple_charts(self, charts_config, dataset_id, update_mode=True):
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
        
        return processed_charts

    def process_charts(self, charts_config, dataset_id, dashboard_title=None, update_mode=True):
        """Main processing method - creates charts and optionally adds them to dashboard"""
        print(f"📊 Processing {len(charts_config)} charts...")
        
        # Create/update charts
        chart_ids = self.create_multiple_charts(charts_config, dataset_id, update_mode)
        
        if not chart_ids:
            print("❌ No charts were created successfully")
            return []
        
        print(f"✅ Successfully processed {len(chart_ids)} charts")
        
        # # If dashboard title provided, create dashboard and add charts
        # if dashboard_title:
        #     print(f"\n🏗️ Creating/updating dashboard '{dashboard_title}'...")
        #     dashboard_id = self.dashboard_manager.create_dashboard(dashboard_title)
            
        #     if dashboard_id:
        #         print(f"🔗 Adding charts to dashboard...")
        #         self.dashboard_manager.add_charts_to_dashboard(dashboard_id, chart_ids)
        #     else:
        #         print("⚠️ Dashboard creation failed - charts created but not added to dashboard")
        # else:
        #     print("ℹ️ No dashboard specified - charts created without dashboard")
        
        return chart_ids

    # Delegate dashboard methods to dashboard_manager
    def get_existing_dashboards(self):
        """Get all existing dashboards - delegates to dashboard manager"""
        return self.dashboard_manager.get_existing_dashboards()
    
    def create_dashboard(self, title="Auto Dashboard"):
        """Create a dashboard - delegates to dashboard manager"""
        return self.dashboard_manager.create_dashboard(title)
    
    def update_dashboard_charts(self, dashboard_id, chart_ids):
        """Add charts to dashboard - delegates to dashboard manager"""
        return self.dashboard_manager.add_charts_to_dashboard(dashboard_id, chart_ids)

    def delete_chart(self, chart_id):
        """Delete a chart by ID"""
        resp = self.session.delete(f"{self.superset_url}/api/v1/chart/{chart_id}", headers=self.headers)
        if resp.status_code == 200:
            print(f"✅ Deleted chart ID: {chart_id}")
            return True
        else:
            print(f"❌ Failed to delete chart {chart_id}: {resp.status_code} - {resp.text}")
            return False

    def get_chart_info(self, chart_id):
        """Get detailed information about a specific chart"""
        resp = self.session.get(f"{self.superset_url}/api/v1/chart/{chart_id}", headers=self.headers)
        if resp.status_code == 200:
            return resp.json()["result"]
        else:
            print(f"❌ Failed to get chart info for {chart_id}: {resp.status_code}")
            return None

    def copy_working_chart(self, source_chart_name, new_chart_name):
        """Copy a working chart by name - integrated from successful copier"""
        # Find the source chart
        resp = self.session.get(f"{self.superset_url}/api/v1/chart/", headers=self.headers)
        if resp.status_code != 200:
            print(f"❌ Failed to list charts: {resp.status_code}")
            return None
        
        charts = resp.json()["result"]
        # print(charts)
        source_chart_id = None
        for chart in charts:
            if chart["slice_name"] == source_chart_name:
                source_chart_id = chart["id"]
                break
        
        if not source_chart_id:
            print(f"❌ Chart '{source_chart_name}' not found")
            return None
        
        # Get the source chart configuration
        resp = self.session.get(f"{self.superset_url}/api/v1/chart/{source_chart_id}", headers=self.headers)
        if resp.status_code != 200:
            print(f"❌ Failed to get chart config: {resp.status_code}")
            return None
        
        source_config = resp.json()["result"]
        print(source_config)
        
        # Extract dataset ID from params or query_context
        dataset_id = None
        try:
            params_str = source_config.get('params', '{}')
            params = json.loads(params_str) if isinstance(params_str, str) else params_str
            
            if 'datasource' in params:
                datasource = params['datasource']
                if '__table' in str(datasource):
                    dataset_id = int(datasource.split('__')[0])
        except (json.JSONDecodeError, ValueError, AttributeError):
            pass
        
        if dataset_id is None:
            try:
                query_context_str = source_config.get('query_context', '{}')
                query_context = json.loads(query_context_str) if isinstance(query_context_str, str) else query_context_str
                
                if 'datasource' in query_context and isinstance(query_context['datasource'], dict):
                    dataset_id = query_context['datasource'].get('id')
            except (json.JSONDecodeError, ValueError, AttributeError):
                pass
        
        if dataset_id is None:
            print("❌ Could not extract dataset ID from source chart")
            return None
        
        # Create new chart with exact same configuration
        new_payload = {
            "slice_name": new_chart_name,
            "viz_type": source_config["viz_type"],
            "datasource_id": dataset_id,
            "datasource_type": "table",
            "params": source_config.get('params', '{}'),
            "query_context": source_config.get('query_context', '{}')
        }
        
        print(f"🔨 Creating copy of '{source_chart_name}' as '{new_chart_name}'...")
        resp = self.session.post(f"{self.superset_url}/api/v1/chart/", headers=self.headers, json=new_payload)
        
        if resp.status_code == 201:
            new_chart_id = resp.json()["id"]
            print(f"✅ Successfully created chart '{new_chart_name}' (ID: {new_chart_id})")
            return new_chart_id
        else:
            print(f"❌ Failed to create chart: {resp.status_code} - {resp.text}")
            return None

    # === DEBUGGING METHODS ===

    def debug_chart_execution(self, chart_id):
        """Debug chart execution by running the query directly"""
        print(f"\n🔍 DEBUGGING CHART {chart_id}")
        
        # Get chart info
        resp = self.session.get(f"{self.superset_url}/api/v1/chart/{chart_id}", headers=self.headers)
        if resp.status_code != 200:
            print(f"❌ Failed to get chart info: {resp.status_code}")
            return
        
        chart_info = resp.json()["result"]
        print(f"📊 Chart name: {chart_info['slice_name']}")
        print(f"📊 Viz type: {chart_info['viz_type']}")
        
        # Try to run the chart query
        query_context = chart_info.get('query_context')
        if query_context:
            print(f"\n🔍 Running chart query...")
            resp = self.session.post(
                f"{self.superset_url}/api/v1/chart/data",
                headers=self.headers,
                json={"query_context": query_context}
            )
            print(f"Query response status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"❌ Query failed: {resp.text}")
            else:
                result = resp.json()
                print(f"✅ Query successful: {len(result.get('result', []))} results")
                if result.get('result'):
                    print(f"Sample data: {result['result'][0] if result['result'] else 'No data'}")

    def test_dataset_query(self, dataset_id):
        """Test if we can access the dataset"""
        print(f"🔍 Testing dataset {dataset_id}...")
        
        # Simple test - just get dataset info
        dataset_info = self.auth.get_dataset_info(dataset_id)
        if dataset_info:
            print(f"✅ Dataset accessible with {len(dataset_info['columns'])} columns")
            return True
        else:
            print(f"❌ Dataset {dataset_id} not accessible")
            return False