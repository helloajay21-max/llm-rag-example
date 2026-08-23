import pandas as pd
import os

# Ensure data folder exists
os.makedirs("data", exist_ok=True)

# Create sample data
data = {
    "date": ["2026-03-01","2026-03-02","2026-03-03","2026-03-04","2026-03-05"],
    "heart_rate": [72,80,65,90,75],
    "steps": [5000,7000,4000,9000,6500],
    "sleep_hours": [6.5,7,5.5,6,7.5],
    "bp_systolic": [120,125,118,135,122]
}

# Convert to DataFrame
df = pd.DataFrame(data)

# Save CSV correctly
file_path = "data/sample_health.csv"
df.to_csv(file_path, index=False)

print(f"✅ File created successfully at: {file_path}")