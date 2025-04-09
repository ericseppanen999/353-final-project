import sqlite3
import pandas as pd
import numpy as np
import re
import matplotlib.pyplot as plt
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_predict

# ----- Load Financial Data -----
db_path = "timekeeping.db"
conn = sqlite3.connect(db_path)
df_fin = pd.read_sql_query("SELECT * FROM financial_data", conn)
conn.close()

# List of numeric columns (target and features)
numeric_cols = [
    "percent_complete", "fee_earned_to_date", "fee_as_per_contract",
    "amount_left_to_bill", "target_fees_per_hour", "actual_fees_per_hour",
    "pre_CA_budget_hours", "pre_CA_actual_hours", "hours_left",
    "months_in_construction", "construction_fee_per_month", "CA_actual_hours",
    "CA_budget_hours", "floor_area", "cost_per_sq_ft", "construction_budget",
    "number_of_units", "corrected_fee_budget_hours", "corrected_fee_actual_hours",
    "fee_per_unit_based_on_higher_fee_value", "fee_per_sf_based_on_higher_fee_value",
    "fee_construction_budget", "corrected_fee_construction_budget"
]

# Convert numeric columns to numbers (errors become NaN)
for col in numeric_cols:
    df_fin[col] = pd.to_numeric(df_fin[col], errors='coerce')

# Drop rows with missing target value
df_fin = df_fin.dropna(subset=["fee_earned_to_date"])

# Set target variable and features.
# We'll predict fee_earned_to_date.
y = df_fin["fee_earned_to_date"]
# Use all numeric columns except fee_earned_to_date as features.
feature_cols = [col for col in numeric_cols if col != "fee_earned_to_date"]
X = df_fin[feature_cols]

# ----- Build the Pipeline and Evaluate the Model -----
pipeline = make_pipeline(
    SimpleImputer(strategy='median'),
    StandardScaler(),
    RandomForestRegressor(n_estimators=200, random_state=42)
)

# Use cross-validation to get a sense of performance.
y_pred_cv = cross_val_predict(pipeline, X, y, cv=5)
df_fin["predicted_fee"] = y_pred_cv

plt.figure(figsize=(8, 6))
plt.scatter(y, y_pred_cv, alpha=0.7)
plt.plot([y.min(), y.max()], [y.min(), y.max()], 'r--')
plt.xlabel("Actual Fee Earned to Date")
plt.ylabel("Predicted Fee Earned to Date")
plt.title("Actual vs. Predicted Fee (Cross-Validated)")
plt.show()

# Train the pipeline on the full data.
pipeline.fit(X, y)

# ----- Function to Clean Project Numbers -----
def clean_project_no(project_no):
    s = str(project_no).strip()
    s = re.sub(r'^[0]+', '', s)  # remove leading zeros
    m = re.match(r'(\d+)', s)     # extract leading digits
    return m.group(1) if m else s

# ----- Predict for a Specific Project -----
project_input = input("Enter a project number to predict fee earned to date: ").strip()
project_input_clean = clean_project_no(project_input)

# Retrieve the corresponding row from df_fin.
row = df_fin[df_fin["project_no"].astype(str).str.strip() == project_input_clean]
if row.empty:
    print(f"No financial data available for project {project_input_clean}")
else:
    X_new = row[feature_cols]
    prediction = pipeline.predict(X_new)
    print(f"Predicted Fee Earned to Date for project {project_input_clean}: ${prediction[0]:,.2f}")
