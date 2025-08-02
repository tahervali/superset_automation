import psycopg2
import pandas as pd

# === CONFIG ===
CSV_FILE = "qualtrics_data.csv"
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "superset"
DB_USER = "superset"
DB_PASSWORD = "superset"

# === TABLE SETUP QUERY ===
create_table_query = """
CREATE TABLE IF NOT EXISTS qualtrics_metrics (
    date DATE PRIMARY KEY,
    nps_score INTEGER,
    csat_score INTEGER,
    ces_score INTEGER,
    response_rate DECIMAL
);
"""
# Add this to ensure date is unique if the table already existed
add_constraint_query = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_type = 'PRIMARY KEY'
          AND table_name = 'qualtrics_metrics'
    ) THEN
        ALTER TABLE qualtrics_metrics
        ADD CONSTRAINT qualtrics_metrics_pkey PRIMARY KEY (date);
    END IF;
END;
$$;
"""

insert_query = """
INSERT INTO qualtrics_metrics (date, nps_score, csat_score, ces_score, response_rate)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (date) DO NOTHING;
"""

def main():
    try:
        print("📥 Reading CSV...")
        df = pd.read_csv(CSV_FILE, parse_dates=["date"])
        rows = df.astype({
            "date": "object",
            "nps_score": "int",
            "csat_score": "int",
            "ces_score": "int",
            "response_rate": "float"
        }).values.tolist()

        print("🔗 Connecting to DB...")
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        conn.autocommit = True
        cur = conn.cursor()

        print("🛠️ Creating table if not exists...")
        cur.execute(create_table_query)
        cur.execute(add_constraint_query)

        print(f"⬆️ Inserting {len(rows)} rows...")
        cur.executemany(insert_query, rows)

        print("✅ Data inserted successfully.")
        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()