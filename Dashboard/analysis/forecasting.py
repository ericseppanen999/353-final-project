import sqlite3
import pandas as pd
import numpy as np
import re
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
import plotly.graph_objects as go

# clean project number
def clean_project_no(project_no):
    s=str(project_no).strip()
    s=re.sub(r'^[0]+','',s)
    m=re.match(r'(\d+)',s)
    return m.group(1)if m else s

# get monthly expenditure
def get_monthly_expenditure(project_no,db_path="timekeeping.db"):
    conn=sqlite3.connect(db_path)
    query=f"""
      SELECT strftime('%Y-%m',T.date)AS month,
             SUM(T.hours_worked*CAST(E.billable_rate AS INTEGER))AS total_expenditure
      FROM time_entries T
      JOIN employees E ON T.employee_id=E.employee_id
      WHERE T.project_no='{project_no}'
      GROUP BY month
      ORDER BY month;
    """
    df=pd.read_sql_query(query,conn)
    conn.close()
    
    if df.empty:
        print(f"No data found for project {project_no}")
        return pd.DataFrame()
    
    df['expenditure']=df['total_expenditure']
    df['ds']=pd.to_datetime(df['month']+"-01")
    
    # exclude current partial month
    current_month=pd.Timestamp.today().to_period('M')
    df=df[df['ds'].dt.to_period('M')<current_month]
    
    df=df[['ds','expenditure']].sort_values('ds').reset_index(drop=True)
    df['month_index']=np.arange(1,len(df)+1)
    return df

# create lag features
def create_lag_features(df,n_lags=5):
    for lag in range(1,n_lags+1):
        df[f'lag_{lag}']=df['expenditure'].shift(lag)
    df=df.dropna().reset_index(drop=True)
    return df

# forecast expenditure
def forecast_expenditure(project_no,forecast_period=3,db_path="timekeeping.db"):
    df=get_monthly_expenditure(project_no,db_path)
    if df.empty or len(df)<5:
        print("Not enough data to forecast.")
        return None

    df_lag=create_lag_features(df.copy(),n_lags=5)
    features=['month_index']+[f'lag_{i}'for i in range(1,6)]
    X=df_lag[features]
    y=df_lag['expenditure']
    
    pipeline=make_pipeline(
        SimpleImputer(strategy='median'),
        StandardScaler(),
        RandomForestRegressor(n_estimators=200,random_state=42)
    )
    pipeline.fit(X,y)

    forecasts=[]
    last_month_index=df['month_index'].iloc[-1]
    last_expenditures=df['expenditure'].iloc[-5:].values.tolist()
    
    for i in range(1,forecast_period+1):
        new_index=last_month_index+i
        new_features=np.array([new_index]+last_expenditures).reshape(1,-1)
        y_pred=pipeline.predict(new_features)[0]
        forecasts.append(y_pred)
        last_expenditures.pop(0)
        last_expenditures.append(y_pred)
    
    last_date=df['ds'].max()
    forecast_dates=[last_date+pd.DateOffset(months=i)for i in range(1,forecast_period+1)]
    forecast_df=pd.DataFrame({'ds':forecast_dates,'forecast_expenditure':forecasts})
    
    # evaluate forecast before returning
    evaluate_forecast_expenditure(project_no,forecast_period=forecast_period,db_path=db_path)
    
    return forecast_df

# evaluate forecast expenditure
def evaluate_forecast_expenditure(project_no,forecast_period=3,test_period=3,db_path="timekeeping.db"):
    df=get_monthly_expenditure(project_no,db_path)
    if len(df)<(forecast_period+test_period):
        print("Not enough data for evaluation.")
        return None
    
    train_df=df.iloc[:len(df)-test_period].copy()
    test_df=df.iloc[len(df)-test_period:].copy()
    
    train_df_lag=create_lag_features(train_df.copy(),n_lags=5)
    features=['month_index']+[f'lag_{i}'for i in range(1,6)]
    X_train=train_df_lag[features]
    y_train=train_df_lag['expenditure']
    
    pipeline=make_pipeline(
        SimpleImputer(strategy='median'),
        StandardScaler(),
        RandomForestRegressor(n_estimators=200,random_state=32)
    )
    pipeline.fit(X_train,y_train)
    
    forecasts=[]
    last_month_index=train_df['month_index'].iloc[-1]
    last_expenditures=train_df['expenditure'].iloc[-5:].values.tolist()
    
    for i in range(1,test_period+1):
        new_index=last_month_index+i
        new_features=np.array([new_index]+last_expenditures).reshape(1,-1)
        y_pred=pipeline.predict(new_features)[0]
        forecasts.append(y_pred)
        last_expenditures.pop(0)
        last_expenditures.append(y_pred)
    
    test_df=test_df.reset_index(drop=True)
    forecast_array=np.array(forecasts)
    actual_array=test_df['expenditure'].values[:test_period]
    mape=np.mean(np.abs(forecast_array-actual_array)/np.abs(actual_array))*100
    
    print("Evaluation Metrics:")
    print("MAPE:",mape)