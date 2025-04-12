# dbscan_clustering.py
import sqlite3
import pandas as pd
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler
from sklearn.cluster import DBSCAN

def load_project_features(db_path="../timekeeping.db"):
  # load and merge project data
  conn=sqlite3.connect(db_path)
  query_cost="""
  SELECT
    T.project_no,
    SUM(T.hours_worked*E.billable_rate) AS total_billable_cost
  FROM time_entries T
  JOIN employees E ON T.employee_id=E.employee_id
  GROUP BY T.project_no
  """
  df_cost=pd.read_sql_query(query_cost,conn)
  query_financial="""
  SELECT
    project_no,
    percent_complete,
    fee_earned_to_date,
    fee_as_per_contract,
    amount_left_to_bill,
    target_fees_per_hour,
    actual_fees_per_hour,
    floor_area,
    cost_per_sq_ft,
    construction_budget,
    number_of_units
  FROM financial_data
  """
  df_fin=pd.read_sql_query(query_financial,conn)
  conn.close()
  df_merged=pd.merge(df_fin,df_cost,on='project_no',how='left')
  df_merged['total_billable_cost']=df_merged['total_billable_cost'].fillna(0)
  return df_merged

def preprocess_for_clustering(df):
  # preprocess data for clustering
  feature_cols=[
    'total_billable_cost',
    'percent_complete',
    'fee_earned_to_date',
    'fee_as_per_contract',
    'amount_left_to_bill',
    'target_fees_per_hour',
    'actual_fees_per_hour',
    'floor_area',
    'cost_per_sq_ft',
    'construction_budget',
    'number_of_units'
  ]
  df_num=df[feature_cols].copy()
  imputer=SimpleImputer(strategy='mean') # impute missing values
  data_imputed=imputer.fit_transform(df_num)
  skew_cols=[
    'total_billable_cost','fee_earned_to_date','fee_as_per_contract',
    'amount_left_to_bill','construction_budget','floor_area'
  ]
  for i,col in enumerate(feature_cols): # log-transform skewed columns
    if col in skew_cols:
      col_data=data_imputed[:,i]
      data_imputed[:,i]=np.sign(col_data)*np.log1p(np.abs(col_data))
  scaler=RobustScaler() # robust scaling
  data_scaled=scaler.fit_transform(data_imputed)
  return data_scaled,df_num.index,feature_cols

def cluster_projects_dbscan(data_scaled,eps=0.5,min_samples=5):
  # run dbscan clustering
  dbscan_model=DBSCAN(eps=eps,min_samples=min_samples)
  labels=dbscan_model.fit_predict(data_scaled)
  return labels,dbscan_model

def run_dbscan_workflow(db_path="../timekeeping.db",eps=0.5,min_samples=5):
  # full dbscan workflow
  df=load_project_features(db_path)
  data_scaled,row_index,feature_cols=preprocess_for_clustering(df)
  labels,dbscan_model=cluster_projects_dbscan(data_scaled,eps=eps,min_samples=min_samples)
  df['cluster_label']=labels # attach cluster labels
  return df,data_scaled,labels
