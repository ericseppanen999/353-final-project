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
    s=str(project_no).strip()
    s=re.sub(r'^[0]+','',s)
    m=re.match(r'(\d+)',s)
    return m.group(1) if m else s

def get_monthly_expenditure(project_no,db_path="timekeeping.db",rate=100.0):
    conn=sqlite3.connect(db_path)
    query=f"""
      SELECT strftime('%Y-%m',date) AS month,SUM(hours_worked) AS total_hours
      FROM time_entries
      WHERE project_no='{project_no}'
      GROUP BY month
      ORDER BY month;
    """
    df=pd.read_sql_query(query,conn)
    conn.close()
    
    if df.empty:
        print(f"No data found for project {project_no}")
        return pd.DataFrame()
    
    df['expenditure']=df['total_hours']*rate
    df['ds']=pd.to_datetime(df['month']+"-01")  # convert month to datetime
    df=df[['ds','expenditure']].sort_values('ds').reset_index(drop=True)
    df['month_index']=np.arange(1,len(df)+1)  # add simple month index
    return df

# create lag features
def create_lag_features(df,n_lags=3):
    for lag in range(1,n_lags+1):
        df[f'lag_{lag}']=df['expenditure'].shift(lag)
    df=df.dropna().reset_index(drop=True)
    return df

# forecast expenditure for next n months
def forecast_expenditure(project_no,forecast_period=3,db_path="timekeeping.db",rate=100.0):
    # get historical monthly expenditure data
    df=get_monthly_expenditure(project_no,db_path,rate)
    if df.empty or len(df)<3:
        print("Not enough data to forecast.")
        return None

    df_lag=create_lag_features(df.copy(),n_lags=3)
    features=['month_index','lag_1','lag_2','lag_3']
    X=df_lag[features]
    y=df_lag['expenditure']
    
    # build regression pipeline
    pipeline=make_pipeline(
        SimpleImputer(strategy='median'),
        StandardScaler(),
        RandomForestRegressor(n_estimators=200,random_state=42)
    )
    pipeline.fit(X,y)

    # recursive forecasting for next forecast_period months
    forecasts=[]
    last_row=df.iloc[-1].copy()  # last observation from original data
    for i in range(1,forecast_period+1):
        new_index=last_row['month_index']+i  # new month index
        lag1=forecasts[-1] if forecasts else last_row['expenditure']  # lag_1
        lag2=df.iloc[-2]['expenditure']  # lag_2
        lag3=df.iloc[-3]['expenditure']  # lag_3
        new_features=np.array([new_index,lag1,lag2,lag3]).reshape(1,-1)
        y_pred=pipeline.predict(new_features)[0]
        forecasts.append(y_pred)
    
    # construct forecast date range
    last_date=df['ds'].max()
    forecast_dates=[last_date+pd.DateOffset(months=i) for i in range(1,forecast_period+1)]
    forecast_df=pd.DataFrame({'ds':forecast_dates,'forecast_expenditure':forecasts})
    return forecast_df

if __name__=="__main__":
    project_no_input=input("Enter project number for expenditure forecast: ").strip()
    project_no_clean=clean_project_no(project_no_input)
    forecast_period=int(input("Enter number of months to forecast: "))
    forecast_df=forecast_expenditure(project_no_clean,forecast_period)
    if forecast_df is not None:
        print(forecast_df)
        plt.figure(figsize=(10,6))
        plt.plot(forecast_df['ds'],forecast_df['forecast_expenditure'],marker='o',linestyle='-',color='blue')
        plt.xlabel("Date")
        plt.ylabel("Forecasted Expenditure ($)")
        plt.title(f"Forecasted Expenditure for Project {project_no_clean}")
        plt.show()
