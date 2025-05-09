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
def get_monthly_expenditure(project_no,db_path="../timekeeping.db"):
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

def last_n_months(df,n=5):
    for i in range(1,n+1):
        df[f'lag_{i}']=df['expenditure'].shift(i)
    df=df.dropna().reset_index(drop=True)
    return df

# forecast expenditure
def forecast_expenditure(project_no,forecast_period=3,db_path="timekeeping.db"):
    df=get_monthly_expenditure(project_no,db_path)
    #print(df.shape)
    if df.empty or len(df)<5:
        print("Not enough data to forecast.")
        return None

    df_lnm=last_n_months(df.copy(),n=5)
    # sorry about the for loop
    features=['month_index']+[f'lag_{i}'for i in range(1,6)]
    X=df_lnm[features]
    y=df_lnm['expenditure']
    
    #like in class:
    pipeline=make_pipeline(
        SimpleImputer(strategy='median'),
        StandardScaler(),
        RandomForestRegressor(n_estimators=200)
    )
    # fit the model
    #print(X.shape,y.shape)
    pipeline.fit(X,y)

    # predict future values
    forecasts=[]
    last_month_index=df['month_index'].iloc[-1]
    last_expenditures=df['expenditure'].iloc[-5:].values.tolist()
    
    for i in range(1,forecast_period+1):
        # for each month in the forecast period
        # create new month index and features

        #print(last_expenditures)
        new_index=last_month_index+i
        new_features=np.array([new_index]+last_expenditures).reshape(1,-1)
        y_pred=pipeline.predict(new_features)[0]
        #print(y_pred)
        # append new pred
        forecasts.append(y_pred)
        # pop the first element and append the new pred
        last_expenditures.pop(0)
        last_expenditures.append(y_pred)
    
    # create forecast dataframe
    last_date=df['ds'].max()
    forecast_dates=[last_date+pd.DateOffset(months=i)for i in range(1,forecast_period+1)]
    forecast_df=pd.DataFrame({'ds':forecast_dates,'forecast_expenditure':forecasts})
    
    # evaluate forecast before returning
    evaluate_forecast_expenditure(project_no,forecast_period=forecast_period,db_path=db_path)
    
    return forecast_df

# evaluate forecast expenditure
def evaluate_forecast_expenditure(project_no,forecast_period=3,test_period=3,db_path="../timekeeping.db"):
    
    # split data into train and test sets,make sure to use the last 5 months,evaluate
    
    df=get_monthly_expenditure(project_no,db_path)
    if len(df)<(forecast_period+test_period):
        print("Not enough data for evaluation.")
        return None
    
    train_df=df.iloc[:len(df)-test_period].copy()
    test_df=df.iloc[len(df)-test_period:].copy()
    # print(train_df.shape,test_df.shape)
    train_df_lag=last_n_months(train_df.copy(),n=5)
    features=['month_index']+[f'lag_{i}'for i in range(1,6)]
    X_train=train_df_lag[features]
    y_train=train_df_lag['expenditure']
    
    pipeline=make_pipeline(
        SimpleImputer(strategy='median'),
        StandardScaler(),
        RandomForestRegressor(n_estimators=200)
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

    # https://en.wikipedia.org/wiki/Mean_absolute_percentage_error
    mape=np.mean(np.abs(forecast_array-actual_array)/np.abs(actual_array))*100
    
    print("Evaluation Metrics:")
    print("MAPE:",mape)