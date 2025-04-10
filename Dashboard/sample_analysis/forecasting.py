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

def clean_project_no(project_no):
    s = str(project_no).strip()
    s = re.sub(r'^[0]+','',s)
    m = re.match(r'(\d+)', s)
    return m.group(1) if m else s

def get_monthly_expenditure(project_no, db_path="timekeeping.db"):
    conn = sqlite3.connect(db_path)
    query = f"""
      SELECT strftime('%Y-%m', T.date) AS month,
             SUM(T.hours_worked * CAST(E.billable_rate AS INTEGER)) AS total_expenditure
      FROM time_entries T
      JOIN employees E ON T.employee_id = E.employee_id
      WHERE T.project_no='{project_no}'
      GROUP BY month
      ORDER BY month;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print(f"No data found for project {project_no}")
        return pd.DataFrame()
    
    # Use the computed total_expenditure (hours * billable_rate) directly.
    df['expenditure'] = df['total_expenditure']
    df['ds'] = pd.to_datetime(df['month'] + "-01")  # convert month to datetime
    df = df[['ds', 'expenditure']].sort_values('ds').reset_index(drop=True)
    df['month_index'] = np.arange(1, len(df) + 1)  # add a simple month index
    return df

# create lag features
def create_lag_features(df, n_lags=3):
    for lag in range(1, n_lags+1):
        df[f'lag_{lag}'] = df['expenditure'].shift(lag)
    df = df.dropna().reset_index(drop=True)
    return df

# forecast expenditure for next n months
def forecast_expenditure(project_no, forecast_period=3, db_path="timekeeping.db"):
    # get historical monthly expenditure data (now based on actual employee billable rates)
    df = get_monthly_expenditure(project_no, db_path)
    if df.empty or len(df) < 3:
        print("Not enough data to forecast.")
        return None

    df_lag = create_lag_features(df.copy(), n_lags=3)
    features = ['month_index', 'lag_1', 'lag_2', 'lag_3']
    X = df_lag[features]
    y = df_lag['expenditure']
    
    # Build regression pipeline
    pipeline = make_pipeline(
        SimpleImputer(strategy='median'),
        StandardScaler(),
        RandomForestRegressor(n_estimators=200, random_state=42)
    )
    pipeline.fit(X, y)

    # Recursive forecasting for next forecast_period months
    forecasts = []
    last_month_index = df['month_index'].iloc[-1]
    # Use the last 3 expenditure values as the starting lags
    last_expenditures = df['expenditure'].iloc[-3:].values.tolist()
    
    for i in range(1, forecast_period+1):
        new_index = last_month_index + i
        # For lag features: lag_1 is the most recent prediction (or last known expenditure if first iteration),
        # lag_2 and lag_3 are from the historical record (updated recursively)
        lag1 = forecasts[-1] if forecasts else last_expenditures[-1]
        lag2 = last_expenditures[-2] if len(last_expenditures) >= 2 else 0
        lag3 = last_expenditures[-3] if len(last_expenditures) >= 3 else 0
        new_features = np.array([new_index, lag1, lag2, lag3]).reshape(1, -1)
        y_pred = pipeline.predict(new_features)[0]
        forecasts.append(y_pred)
        # Update last_expenditures with the new prediction (drop the oldest)
        last_expenditures.pop(0)
        last_expenditures.append(y_pred)
    
    # Construct forecast date range starting from the last observed date
    last_date = df['ds'].max()
    forecast_dates = [last_date + pd.DateOffset(months=i) for i in range(1, forecast_period+1)]
    forecast_df = pd.DataFrame({'ds': forecast_dates, 'forecast_expenditure': forecasts})
    return forecast_df

if __name__ == "__main__":
    project_no_input = input("Enter project number for expenditure forecast: ").strip()
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
