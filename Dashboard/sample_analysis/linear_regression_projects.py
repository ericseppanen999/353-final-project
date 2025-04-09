import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

def forecast_project_sklearn(project_no, db_path="timekeeping.db", forecast_period=1):
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
        print(f"No data available for project {project_no}.")
        return None, None

    df['ds'] = pd.to_datetime(df['month'] + "-01")

    df['ordinal'] = df['ds'].map(datetime.toordinal)
    
    X = df[['ordinal']]
    y = df['total_hours']

    model = LinearRegression()
    model.fit(X, y)

    last_date = df['ds'].max()
    next_date = last_date + relativedelta(months=forecast_period)
    next_ord = np.array([[next_date.toordinal()]])
    y_pred = model.predict(next_ord)
    
    plt.figure(figsize=(10, 6))
    plt.scatter(df['ds'], y, color="blue", label="Actual Hours")
    plt.plot(df['ds'], model.predict(X), color="red", label="Fitted Trend")
    plt.scatter(next_date, y_pred, color="green", s=100, label="Forecast")
    plt.xlabel("Date")
    plt.ylabel("Total Hours")
    plt.title(f"Forecast for Project {project_no}")
    plt.legend()
    plt.show()
    
    return next_date, y_pred[0]

if __name__ == "__main__":
    project_no = input("Enter project number for forecast: ").strip()
    forecast_date, forecast_hours = forecast_project_sklearn(project_no)
    if forecast_date is not None:
        print(f"Forecast for project {project_no} on {forecast_date.date()}: {forecast_hours:.2f} hours")
