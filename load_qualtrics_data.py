import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime

# === CONFIG ===
CSV_FILE = "enhanced_qualtrics_data.csv"
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "superset"
DB_USER = "superset"
DB_PASSWORD = "superset"

# === ENHANCED TABLE SETUP QUERY ===
create_table_query = """
CREATE TABLE IF NOT EXISTS qualtrics_metrics2 (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    
    -- Core CX Metrics
    nps_score INTEGER,
    csat_score INTEGER,
    ces_score DECIMAL(3,2),
    response_rate DECIMAL(5,2),
    completion_rate DECIMAL(5,2),
    responses_count INTEGER,
    cx_composite_score DECIMAL(5,2),
    
    -- Category Satisfaction Scores (1-5 scale)
    product_satisfaction DECIMAL(3,2),
    support_satisfaction DECIMAL(3,2),
    ease_of_use DECIMAL(3,2),
    value_score DECIMAL(3,2),
    
    -- Temporal Dimensions
    day_of_week VARCHAR(10),
    month VARCHAR(10),
    week_number INTEGER,
    quarter VARCHAR(2),
    is_weekend INTEGER,
    
    -- Calculated Performance Tiers
    performance_tier VARCHAR(20),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Create indexes for better query performance
create_indexes_query = """
CREATE INDEX IF NOT EXISTS idx_qualtrics_date ON qualtrics_metrics2(date);
CREATE INDEX IF NOT EXISTS idx_qualtrics_month ON qualtrics_metrics2(month);
CREATE INDEX IF NOT EXISTS idx_qualtrics_quarter ON qualtrics_metrics2(quarter);
CREATE INDEX IF NOT EXISTS idx_qualtrics_weekend ON qualtrics_metrics2(is_weekend);
CREATE INDEX IF NOT EXISTS idx_qualtrics_performance ON qualtrics_metrics2(performance_tier);
CREATE INDEX IF NOT EXISTS idx_qualtrics_nps ON qualtrics_metrics2(nps_score);
CREATE INDEX IF NOT EXISTS idx_qualtrics_composite ON qualtrics_metrics2(cx_composite_score);
"""

# Insert query for all columns
insert_query = """
INSERT INTO qualtrics_metrics2 (
    date, nps_score, csat_score, ces_score, response_rate, completion_rate,
    responses_count, cx_composite_score, product_satisfaction, support_satisfaction,
    ease_of_use, value_score, day_of_week, month, week_number, quarter,
    is_weekend, performance_tier
)
VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
ON CONFLICT (date) DO UPDATE SET
    nps_score = EXCLUDED.nps_score,
    csat_score = EXCLUDED.csat_score,
    ces_score = EXCLUDED.ces_score,
    response_rate = EXCLUDED.response_rate,
    completion_rate = EXCLUDED.completion_rate,
    responses_count = EXCLUDED.responses_count,
    cx_composite_score = EXCLUDED.cx_composite_score,
    product_satisfaction = EXCLUDED.product_satisfaction,
    support_satisfaction = EXCLUDED.support_satisfaction,
    ease_of_use = EXCLUDED.ease_of_use,
    value_score = EXCLUDED.value_score,
    day_of_week = EXCLUDED.day_of_week,
    month = EXCLUDED.month,
    week_number = EXCLUDED.week_number,
    quarter = EXCLUDED.quarter,
    is_weekend = EXCLUDED.is_weekend,
    performance_tier = EXCLUDED.performance_tier,
    updated_at = CURRENT_TIMESTAMP;
"""

def calculate_performance_tier(cx_score):
    """Calculate performance tier based on composite CX score"""
    if cx_score >= 80:
        return 'Excellent'
    elif cx_score >= 75:
        return 'Good'
    elif cx_score >= 70:
        return 'Average'
    else:
        return 'Needs Improvement'

def prepare_data(df):
    """Prepare and validate data for insertion"""
    print("🔧 Preparing data...")
    
    # Handle missing values
    df = df.fillna({
        'nps_score': 0,
        'csat_score': 0,
        'ces_score': 0,
        'response_rate': 0,
        'completion_rate': 0,
        'responses_count': 0,
        'cx_composite_score': 0,
        'product_satisfaction': 0,
        'support_satisfaction': 0,
        'ease_of_use': 0,
        'value_score': 0,
        'week_number': 1,
        'is_weekend': 0
    })
    
    # Ensure required columns exist or create them
    if 'week_number' not in df.columns:
        df['week_number'] = pd.to_datetime(df['date']).dt.isocalendar().week
    
    if 'performance_tier' not in df.columns:
        df['performance_tier'] = df['cx_composite_score'].apply(calculate_performance_tier)
    
    # Data type conversions
    df['date'] = pd.to_datetime(df['date'])
    df['nps_score'] = df['nps_score'].astype(int)
    df['csat_score'] = df['csat_score'].astype(int)
    df['responses_count'] = df['responses_count'].astype(int)
    df['week_number'] = df['week_number'].astype(int)
    df['is_weekend'] = df['is_weekend'].astype(int)
    
    # Convert DataFrame to list of tuples for insertion
    columns = [
        'date', 'nps_score', 'csat_score', 'ces_score', 'response_rate',
        'completion_rate', 'responses_count', 'cx_composite_score',
        'product_satisfaction', 'support_satisfaction', 'ease_of_use',
        'value_score', 'day_of_week', 'month', 'week_number', 'quarter',
        'is_weekend', 'performance_tier'
    ]
    
    # Ensure all required columns exist
    for col in columns:
        if col not in df.columns:
            print(f"⚠️ Missing column '{col}', creating with default values")
            if col in ['day_of_week', 'month', 'quarter', 'performance_tier']:
                df[col] = 'Unknown'
            else:
                df[col] = 0
    
    rows = df[columns].values.tolist()
    return rows

def validate_connection(conn):
    """Test database connection and permissions"""
    try:
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"✅ Connected to PostgreSQL: {version[0]}")
        
        # Test table creation permissions
        cur.execute("SELECT current_user, current_database();")
        user_db = cur.fetchone()
        print(f"✅ User: {user_db[0]}, Database: {user_db[1]}")
        
        cur.close()
        return True
    except Exception as e:
        print(f"❌ Connection validation failed: {e}")
        return False

def main():
    try:
        # Read CSV file
        print("📥 Reading CSV file...")
        if not pd.io.common.file_exists(CSV_FILE):
            print(f"❌ CSV file '{CSV_FILE}' not found!")
            print("💡 Make sure you have generated the enhanced dataset first.")
            return
        
        df = pd.read_csv(CSV_FILE)
        print(f"✅ Loaded {len(df)} records from CSV")
        print(f"📊 Columns: {list(df.columns)}")
        
        # Show data sample
        print(f"\n📋 Sample data:")
        print(df.head(3).to_string(index=False))
        
        # Prepare data
        rows = prepare_data(df)
        print(f"✅ Prepared {len(rows)} rows for insertion")
        
        # Connect to database
        print(f"\n🔗 Connecting to PostgreSQL...")
        print(f"Host: {DB_HOST}:{DB_PORT}, Database: {DB_NAME}, User: {DB_USER}")
        
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True
        
        # Validate connection
        if not validate_connection(conn):
            return
        
        cur = conn.cursor()
        
        # Create table and indexes
        print(f"\n🛠️ Creating table structure...")
        cur.execute(create_table_query)
        print("✅ Table 'qualtrics_metrics2' created/verified")
        
        print("🔍 Creating indexes...")
        cur.execute(create_indexes_query)
        print("✅ Indexes created/verified")
        
        # Insert data
        print(f"\n⬆️ Inserting {len(rows)} rows...")
        
        # Insert in batches for better performance
        batch_size = 100
        inserted_count = 0
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            cur.executemany(insert_query, batch)
            inserted_count += len(batch)
            
            if inserted_count % 500 == 0 or inserted_count == len(rows):
                print(f"  📈 Processed {inserted_count}/{len(rows)} records...")
        
        # Verify insertion
        cur.execute("SELECT COUNT(*) FROM qualtrics_metrics2;")
        total_count = cur.fetchone()[0]
        
        # Get date range
        cur.execute("SELECT MIN(date), MAX(date) FROM qualtrics_metrics2;")
        date_range = cur.fetchone()
        
        # Get some statistics
        cur.execute("""
            SELECT 
                ROUND(AVG(nps_score), 1) as avg_nps,
                ROUND(AVG(csat_score), 1) as avg_csat,
                ROUND(AVG(cx_composite_score), 1) as avg_cx,
                COUNT(DISTINCT performance_tier) as tier_count
            FROM qualtrics_metrics2;
        """)
        stats = cur.fetchone()
        
        print(f"\n✅ Data insertion completed successfully!")
        print(f"📊 Database Summary:")
        print(f"   Total records: {total_count}")
        print(f"   Date range: {date_range[0]} to {date_range[1]}")
        print(f"   Average NPS: {stats[0]}")
        print(f"   Average CSAT: {stats[1]}")
        print(f"   Average CX Score: {stats[2]}")
        print(f"   Performance tiers: {stats[3]}")
        
        # Show performance tier distribution
        cur.execute("""
            SELECT performance_tier, COUNT(*) as count, 
                   ROUND(COUNT(*)::decimal / (SELECT COUNT(*) FROM qualtrics_metrics2) * 100, 1) as percentage
            FROM qualtrics_metrics2 
            GROUP BY performance_tier 
            ORDER BY count DESC;
        """)
        
        print(f"\n🎯 Performance Tier Distribution:")
        for tier_data in cur.fetchall():
            print(f"   {tier_data[0]}: {tier_data[1]} days ({tier_data[2]}%)")
            
        cur.close()
        conn.close()
        
        print(f"\n🎉 Ready for Superset!")
        print(f"💡 Your dataset ID in Superset should point to the 'qualtrics_metrics2' table")
        print(f"💡 You can now run your Superset automation scripts")
        
    except FileNotFoundError:
        print(f"❌ CSV file '{CSV_FILE}' not found!")
        print("💡 Please ensure the enhanced dataset CSV file exists in the current directory")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        print("💡 Check your database connection settings and permissions")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()