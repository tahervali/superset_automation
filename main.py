#!/usr/bin/env python3
"""
Main script to create Superset charts and dashboards.
Run this file to execute the chart creation process.
"""

import sys
from auth import SupersetAuth
from chart_creator import SupersetChartCreator
from chart_configs import (
    SUPERSET_CONFIG, 
    DATASET_ID, 
    DASHBOARD_ID, 
    DASHBOARD_TITLE,
    CHARTS_CONFIG,
    UPDATE_MODE,
    AUTO_UPDATE_DASHBOARD
)

def main():
    try:
        # Initialize authentication
        auth = SupersetAuth(
            superset_url=SUPERSET_CONFIG["url"],
            username=SUPERSET_CONFIG["username"], 
            password=SUPERSET_CONFIG["password"]
        )
        
        # Authenticate
        session, headers = auth.authenticate()
        
        # Initialize chart creator
        chart_creator = SupersetChartCreator(auth)
        
        # Create or use existing dashboard
        dashboard_id = DASHBOARD_ID
        if AUTO_UPDATE_DASHBOARD:
            if dashboard_id:
                # Verify the specified dashboard exists
                resp = chart_creator.session.get(f"{SUPERSET_CONFIG['url']}/api/v1/dashboard/{dashboard_id}", headers=chart_creator.headers)
                if resp.status_code != 200:
                    print(f"⚠️ Dashboard ID {dashboard_id} not found, creating new one...")
                    dashboard_id = None
                else:
                    dashboard_title = resp.json()["result"]["dashboard_title"]
                    print(f"✅ Using existing dashboard '{dashboard_title}' (ID: {dashboard_id})")
            
            if not dashboard_id:
                dashboard_id = chart_creator.create_dashboard(DASHBOARD_TITLE)
                if not dashboard_id:
                    print("❌ Could not create/find dashboard. Continuing with chart creation...")
        
        # Create/update all charts from configuration
        processed_charts = chart_creator.create_multiple_charts(
            CHARTS_CONFIG, 
            DATASET_ID, 
            dashboard_id if AUTO_UPDATE_DASHBOARD else None,
            UPDATE_MODE
        )
        
        # Summary
        action = "processed" if UPDATE_MODE else "created"
        print(f"\n🎉 Successfully {action} {len(processed_charts)} out of {len(CHARTS_CONFIG)} charts.")
        
        if processed_charts:
            print(f"📊 Chart IDs: {processed_charts}")
        
        if dashboard_id:
            print(f"🌐 View dashboard: {SUPERSET_CONFIG['url']}/superset/dashboard/{dashboard_id}/")
            if not AUTO_UPDATE_DASHBOARD:
                print(f"💡 To add charts to dashboard, set AUTO_UPDATE_DASHBOARD=True in chart_configs.py")
        
        print("\n✨ Process completed!")
        
        # Display mode information
        mode_info = []
        if UPDATE_MODE:
            mode_info.append("UPDATE mode (existing charts will be updated)")
        else:
            mode_info.append("CREATE mode (new charts will always be created)")
            
        if AUTO_UPDATE_DASHBOARD:
            mode_info.append("Dashboard auto-update enabled")
        else:
            mode_info.append("Dashboard auto-update disabled")
            
        print(f"ℹ️  Running in: {' | '.join(mode_info)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()