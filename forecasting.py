import sqlite3
import pandas as pd
import numpy as np
import re
import sys
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor

# ----- Helper to clean project numbers -----
def clean_project_no(project_no):
    s = str(project_no).strip()
    s = re.sub(r'^[0]+', '', s)  # remove leading zeros
    m = re.match(r'(\d+)', s)     # extract leading digits so "1712A" -> "1712"
    return m.group(1) if m else s

# ----- Get Monthly Expenditure ----- 
def get_monthly_expenditure(project_no, db_path="timekeeping.db", rate=100.0):
    """
    Aggregate monthly hours for the given project from time_entries,
    compute expenditure using a fixed hourly rate.
    """
    conn = sqlite3.connect(db_path)
    query = f"""
      SELECT strftime('%Y-%m', date) AS month, SUM(hours_worked) AS total_hours
      FROM time_entries
      WHERE project_no = '{project_no}'
      GROUP BY month
      ORDER BY month;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print(f"No data found for project {project_no}")
        return pd.DataFrame()
    
    df['expenditure'] = df['total_hours'] * rate
    # Convert month to datetime (assume first day of month)
    df['ds'] = pd.to_datetime(df['month'] + "-01")
    df = df[['ds', 'expenditure']].sort_values('ds').reset_index(drop=True)
    # Add a simple month index starting at 1
    df['month_index'] = np.arange(1, len(df)+1)
    return df

# ----- Create Lag Features -----
def create_lag_features(df, n_lags=3):
    for lag in range(1, n_lags+1):
        df[f'lag_{lag}'] = df['expenditure'].shift(lag)
    df = df.dropna().reset_index(drop=True)
    return df

# ----- Forecast Expenditure for Next n Months -----
def forecast_expenditure(project_no, forecast_period=3, db_path="timekeeping.db", rate=100.0):
    # Get historical monthly expenditure data.
    df = get_monthly_expenditure(project_no, db_path, rate)
    if df.empty or len(df) < 3:
        print("Not enough data to forecast.")
        return None

    df_lag = create_lag_features(df.copy(), n_lags=3)
    features = ['month_index', 'lag_1', 'lag_2', 'lag_3']
    X = df_lag[features]
    y = df_lag['expenditure']
    
    # Build a regression pipeline
    pipeline = make_pipeline(
        SimpleImputer(strategy='median'),
        StandardScaler(),
        RandomForestRegressor(n_estimators=200, random_state=42)
    )
    pipeline.fit(X, y)

    # Recursive forecasting for next forecast_period months.
    forecasts = []
    # Last observation from the original data (without lag creation, so we have the actual last month)
    last_row = df.iloc[-1].copy()
    for i in range(1, forecast_period + 1):
        # Create new features for the next month:
        # New month index is last month index + i.
        new_index = last_row['month_index'] + i
        # Use the last 3 months expenditures from df (or forecasts if available).
        # For lag_1 use forecast of previous iteration if exists; otherwise use last observed value.
        lag1 = forecasts[-1] if forecasts else last_row['expenditure']
        # For lag_2 and lag_3, use the previous values from df.
        lag2 = df.iloc[-2]['expenditure']
        lag3 = df.iloc[-3]['expenditure']
        new_features = np.array([new_index, lag1, lag2, lag3]).reshape(1, -1)
        y_pred = pipeline.predict(new_features)[0]
        forecasts.append(y_pred)
        # For recursive forecasting, you could update df if desired.
    
    # Construct forecast date range: the next forecast_period months.
    last_date = df['ds'].max()
    forecast_dates = [last_date + pd.DateOffset(months=i) for i in range(1, forecast_period+1)]
    forecast_df = pd.DataFrame({'ds': forecast_dates, 'forecast_expenditure': forecasts})
    return forecast_df

if __name__ == "__main__":
    project_no_input = input("Enter project number for expenditure forecast: ").strip()
    # Clean project number: e.g., "1712A" becomes "1712"
    project_no_clean = clean_project_no(project_no_input)
    
    forecast_period = int(input("Enter number of months to forecast: "))
    forecast_df = forecast_expenditure(project_no_clean, forecast_period)
    if forecast_df is not None:
        print(forecast_df)
        plt.figure(figsize=(10,6))
        plt.plot(forecast_df['ds'], forecast_df['forecast_expenditure'], marker='o', linestyle='-', color='blue')
        plt.xlabel("Date")
        plt.ylabel("Forecasted Expenditure ($)")
        plt.title(f"Forecasted Expenditure for Project {project_no_clean}")
        plt.show()
