import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

def load_time_entries(db_path="timekeeping.db"):
    # load time entries from db
    conn=sqlite3.connect(db_path)
    query="""
    SELECT T.employee_id,E.name,T.date,T.hours_worked
    FROM time_entries T
    JOIN employees E ON T.employee_id=E.employee_id
    """
    df=pd.read_sql_query(query,conn)
    conn.close()
    df['date']=pd.to_datetime(df['date'])
    df['day_of_week']=df['date'].dt.dayofweek
    return df

def compute_daily_summary(df):
    # calculate daily summary
    df_daily=df.groupby(['employee_id','name','date']).agg({'hours_worked':'sum'}).reset_index()
    df_daily['overtime']=df_daily['hours_worked'].apply(lambda x:max(0,x-8))
    df_daily['weekday']=df_daily['date'].dt.dayofweek
    df_daily['is_weekend']=df_daily['weekday']>=5
    return df_daily

def compute_monthly_excess(df,baseline=7.5*5*4):
    # calculate monthly excess
    df_monthly=df.copy()
    df_monthly['month']=df_monthly['date'].dt.to_period("M").astype(str)
    monthly_hours=df_monthly.groupby(['employee_id','name','month'])['hours_worked'].sum().reset_index()
    monthly_hours['excess']=monthly_hours['hours_worked'].apply(lambda x:max(0,x-baseline))
    avg_excess=monthly_hours.groupby(['employee_id','name'])['excess'].mean().reset_index()
    avg_excess=avg_excess.rename(columns={'excess':'avg_monthly_excess'})
    return avg_excess

def compute_burnout_metrics(df_daily,df_time,baseline=7.5*5*4):
    # calculate burnout metrics
    agg_metrics=df_daily.groupby(['employee_id','name']).agg(
        total_days=('date','nunique'),
        total_hours=('hours_worked','sum'),
        total_overtime=('overtime','sum'),
        weekend_days=('is_weekend','sum')
    ).reset_index()
    agg_metrics['avg_daily_hours']=agg_metrics['total_hours']/agg_metrics['total_days']
    agg_metrics['avg_daily_overtime']=agg_metrics['total_overtime']/agg_metrics['total_days']
    agg_metrics['weekend_frequency']=agg_metrics['weekend_days']/agg_metrics['total_days']
    avg_excess=compute_monthly_excess(df_time,baseline)
    agg_metrics=agg_metrics.merge(avg_excess,on=["employee_id","name"],how="left")
    agg_metrics['avg_monthly_excess']=agg_metrics['avg_monthly_excess'].fillna(0)
    agg_metrics['burnout_score']=(
         agg_metrics['avg_daily_overtime']+
         (agg_metrics['weekend_frequency']*2)+
         (agg_metrics['avg_monthly_excess']/50)+
         (agg_metrics['total_days']/10000)
    )
    return agg_metrics

def get_burnout_analysis(db_path="timekeeping.db",baseline=7.5*5*4):
    # load entries and compute burnout
    df_time=load_time_entries(db_path)
    if df_time.empty:
        return pd.DataFrame()
    df_daily=compute_daily_summary(df_time)
    burnout_metrics=compute_burnout_metrics(df_daily,df_time,baseline)
    return burnout_metrics

if __name__=="__main__":
    # print burnout analysis
    analysis_df=get_burnout_analysis("timekeeping.db")
    print("Burnout Analysis:")
    print(analysis_df[['employee_id','name','total_days','avg_daily_hours','avg_daily_overtime',
                         'weekend_frequency','avg_monthly_excess','burnout_score']])
