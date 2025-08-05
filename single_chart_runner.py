# Script to create or update a single Superset chart for debugging
from chart_configs import SUPERSET_CONFIG, DATASET_ID, CHARTS_CONFIG
from auth import SupersetAuth
from chart_creator import SupersetChartCreator
import sys

if __name__ == "__main__":
    print("\n=== Superset Single Chart Runner ===\n")
    # List charts
    for idx, chart in enumerate(CHARTS_CONFIG):
        print(f"{idx+1}. {chart['name']}")
    print("")
    try:
        choice = input(f"Select chart to create/update (1-{len(CHARTS_CONFIG)}): ").strip()
        idx = int(choice) - 1
        if idx < 0 or idx >= len(CHARTS_CONFIG):
            print("❌ Invalid selection.")
            sys.exit(1)
        chart_config = CHARTS_CONFIG[idx]
        print(f"\n➡️  Processing chart: {chart_config['name']}")
        # Authenticate
        auth = SupersetAuth(
            superset_url=SUPERSET_CONFIG["url"],
            username=SUPERSET_CONFIG["username"],
            password=SUPERSET_CONFIG["password"]
        )
        session, headers = auth.authenticate()
        chart_creator = SupersetChartCreator(auth)
        dataset_info = auth.get_dataset_info(DATASET_ID)
        if not dataset_info:
            print("❌ Could not fetch dataset info.")
            sys.exit(1)
        # Create or update chart
        chart_id = chart_creator.create_or_update_chart(chart_config, DATASET_ID, dataset_info, chart_creator.get_existing_charts(DATASET_ID))
        if chart_id:
            print(f"✅ Chart '{chart_config['name']}' processed (ID: {chart_id})")
        else:
            print(f"❌ Failed to process chart '{chart_config['name']}'")
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
