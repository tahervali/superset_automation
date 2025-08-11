import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

def generate_enhanced_qualtrics_data():
    """Generate realistic Qualtrics data with meaningful patterns and fluctuations"""
    
    # Date range: 6 months of daily data
    start_date = datetime(2024, 7, 1)
    end_date = datetime(2024, 12, 31)
    dates = pd.date_range(start_date, end_date, freq='D')
    
    data = []
    
    for i, date in enumerate(dates):
        # Base metrics with realistic ranges
        base_nps = 45
        base_csat = 75
        base_ces = 60
        base_response_rate = 78
        
        # Day of week effects (weekends typically lower engagement)
        day_of_week = date.weekday()
        weekend_factor = 0.95 if day_of_week >= 5 else 1.0
        
        # Monthly trends (improvement over time with some setbacks)
        month_progress = (date.month - 7) / 5  # 0 to 1 over 6 months
        trend_factor = 1 + (month_progress * 0.15)  # 15% improvement trend
        
        # Seasonal effects
        if date.month in [11, 12]:  # Holiday season stress
            seasonal_factor = 0.92
        elif date.month in [7, 8]:  # Summer vacation period
            seasonal_factor = 1.05
        else:
            seasonal_factor = 1.0
        
        # Event-based fluctuations (simulate product launches, issues, etc.)
        event_factor = 1.0
        
        # Major product launch (positive impact)
        if datetime(2024, 8, 15) <= date <= datetime(2024, 8, 25):
            event_factor = 1.12
        
        # System outage period (negative impact)
        elif datetime(2024, 9, 10) <= date <= datetime(2024, 9, 15):
            event_factor = 0.75
        
        # Holiday promotion success
        elif datetime(2024, 11, 25) <= date <= datetime(2024, 12, 5):
            event_factor = 1.08
        
        # End of year issues
        elif datetime(2024, 12, 20) <= date <= datetime(2024, 12, 30):
            event_factor = 0.88
        
        # Random daily variation
        daily_noise = np.random.normal(1, 0.08)  # 8% standard deviation
        
        # Calculate final factors
        total_factor = weekend_factor * trend_factor * seasonal_factor * event_factor * daily_noise
        
        # Generate metrics with correlations
        nps_score = max(0, min(100, int(base_nps * total_factor + np.random.normal(0, 3))))
        
        # CSAT correlates with NPS but has its own variation
        csat_correlation = 0.7
        csat_score = max(0, min(100, int(
            base_csat * total_factor + 
            (nps_score - base_nps) * csat_correlation + 
            np.random.normal(0, 2)
        )))
        
        # CES (Customer Effort Score) - inverse relationship with satisfaction
        ces_base_factor = 0.9 if nps_score > 50 else 1.1
        ces_score = max(1, min(7, int(
            base_ces * ces_base_factor * (1/total_factor) + 
            np.random.normal(0, 2)
        )))
        
        # Response rate correlates with engagement
        response_rate = max(30, min(95, 
            base_response_rate * total_factor * 1.02 + np.random.normal(0, 1.5)
        ))
        
        # Additional metrics for richer analysis
        
        # Survey completion rate (related to response rate)
        completion_rate = max(60, min(98, 
            response_rate * 0.95 + np.random.normal(0, 2)
        ))
        
        # Number of responses (varies by day and engagement)
        base_responses = 150
        responses_count = max(50, int(
            base_responses * (response_rate/78) * weekend_factor + 
            np.random.normal(0, 20)
        ))
        
        # Customer segment performance (simulate different customer types)
        segments = ['Enterprise', 'SMB', 'Startup', 'Individual']
        segment_weights = [0.3, 0.35, 0.25, 0.1]
        
        # Category scores (different aspects of service)
        product_satisfaction = max(1, min(5, 
            3.5 + (nps_score - 45) * 0.02 + np.random.normal(0, 0.3)
        ))
        
        support_satisfaction = max(1, min(5, 
            3.3 + (csat_score - 75) * 0.02 + np.random.normal(0, 0.4)
        ))
        
        ease_of_use = max(1, min(5, 
            3.6 + (7 - ces_score) * 0.1 + np.random.normal(0, 0.3)
        ))
        
        # Value perception
        value_score = max(1, min(5, 
            3.4 + (nps_score - 45) * 0.015 + np.random.normal(0, 0.35)
        ))
        
        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'nps_score': nps_score,
            'csat_score': csat_score,
            'ces_score': ces_score,
            'response_rate': round(response_rate, 1),
            'completion_rate': round(completion_rate, 1),
            'responses_count': responses_count,
            'product_satisfaction': round(product_satisfaction, 2),
            'support_satisfaction': round(support_satisfaction, 2),
            'ease_of_use': round(ease_of_use, 2),
            'value_score': round(value_score, 2),
            'day_of_week': date.strftime('%A'),
            'month': date.strftime('%B'),
            'week_number': date.isocalendar()[1],
            'is_weekend': 1 if day_of_week >= 5 else 0,
            'quarter': f"Q{(date.month-1)//3 + 1}",
            # Calculated fields for analysis
            'cx_composite_score': round(
                (nps_score * 0.3 + csat_score * 0.3 + (8-ces_score) * 12.5 * 0.2 + response_rate * 0.2), 1
            )
        })
    
    return pd.DataFrame(data)

# Generate the enhanced dataset
df = generate_enhanced_qualtrics_data()

# Display summary statistics
print("📊 Enhanced Qualtrics Dataset Summary")
print("="*50)
print(f"Date Range: {df['date'].min()} to {df['date'].max()}")
print(f"Total Records: {len(df)}")
print(f"Columns: {len(df.columns)}")

print("\n📈 Key Metrics Overview:")
metrics = ['nps_score', 'csat_score', 'ces_score', 'response_rate', 'cx_composite_score']
for metric in metrics:
    print(f"{metric.upper()}: "
          f"Min={df[metric].min():.1f}, "
          f"Max={df[metric].max():.1f}, "
          f"Avg={df[metric].mean():.1f}, "
          f"Std={df[metric].std():.1f}")

print("\n🎯 Notable Patterns Built In:")
print("- Weekend effect: Lower engagement on weekends")
print("- Seasonal trends: Summer boost, holiday stress")
print("- Product launch spike: Aug 15-25")
print("- System outage dip: Sep 10-15") 
print("- Holiday promotion: Nov 25 - Dec 5")
print("- Year-end challenges: Dec 20-30")
print("- Overall improvement trend over 6 months")
print("- Realistic correlations between metrics")

# Save to CSV
output_filename = 'enhanced_qualtrics_data.csv'
df.to_csv(output_filename, index=False)
print(f"\n💾 Data saved to: {output_filename}")

# Show sample data
print(f"\n📋 Sample Data (First 5 rows):")
print(df.head().to_string(index=False))

print(f"\n📊 Weekend vs Weekday Comparison:")
weekend_avg = df[df['is_weekend'] == 1]['cx_composite_score'].mean()
weekday_avg = df[df['is_weekend'] == 0]['cx_composite_score'].mean()
print(f"Weekend Average CX Score: {weekend_avg:.1f}")
print(f"Weekday Average CX Score: {weekday_avg:.1f}")
print(f"Weekend Impact: {((weekend_avg/weekday_avg - 1) * 100):+.1f}%")