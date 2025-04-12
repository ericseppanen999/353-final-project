import sqlite3
import pandas as pd
import numpy as np

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import QuantileTransformer, FunctionTransformer
from sklearn.cluster import KMeans
from sklearn.pipeline import make_pipeline


def load_project_features(db_path):
    conn=sqlite3.connect(db_path)

    query_cost="""SELECT T.project_no,SUM(T.hours_worked*E.billable_rate) AS total_billable_cost FROM time_entries T
    JOIN employees E ON T.employee_id=E.employee_id GROUP BY T.project_no"""
    df_cost=pd.read_sql_query(query_cost,conn)

    query_financial="""SELECT project_no,percent_complete,fee_earned_to_date,fee_as_per_contract,
        amount_left_to_bill,target_fees_per_hour,actual_fees_per_hour,floor_area,cost_per_sq_ft,
        construction_budget,number_of_units FROM financial_data"""
    df_fin=pd.read_sql_query(query_financial,conn)
    conn.close()
    #print(df_fin.describe())


    # join on project no
    df_merged=pd.merge(df_fin,df_cost,on="project_no",how="left")
    df_merged["total_billable_cost"]=df_merged["total_billable_cost"].fillna(0)
    return df_merged

def log_transform_skewed(X):
    # should we use a set here?
    # cols that are skewed and need log transformation
    skew_cols={"total_billable_cost","fee_earned_to_date","fee_as_per_contract","amount_left_to_bill","construction_budget","floor_area",}

    # cols to be used in pipeline
    feature_cols=["total_billable_cost","percent_complete","fee_earned_to_date",
        "fee_as_per_contract","amount_left_to_bill","target_fees_per_hour","actual_fees_per_hour",
        "floor_area","cost_per_sq_ft","construction_budget","number_of_units"]
    Xc=X.copy() # do we need to avoid mutating?

    for col in skew_cols:
        if col in feature_cols:
            idx=feature_cols.index(col)
            col_data=Xc[:,idx]
            #print(f"skewed col {col} with data {col_data[:10]}")
            #maybe need check for negatives
            #print("idx",idx)
            Xc[:,idx]=np.sign(col_data)*np.log1p(np.abs(col_data))

    return Xc

def run_kmeans(db_path,n_clusters=3):
    df=load_project_features(db_path)
    feature_cols=["total_billable_cost","percent_complete","fee_earned_to_date","fee_as_per_contract","amount_left_to_bill",
        "target_fees_per_hour","actual_fees_per_hour","floor_area","cost_per_sq_ft","construction_budget","number_of_units"]

    X=df[feature_cols].values
    log_transformer = FunctionTransformer(log_transform_skewed,validate=False)

    pipeline=make_pipeline(
        SimpleImputer(strategy="mean"),
        log_transformer,
        QuantileTransformer(output_distribution="normal"),
        KMeans(n_clusters=n_clusters, random_state=42)
    )
    pipeline.fit(X)

    # retrieve cluster labels from the KMeans step
    kmeans_step=pipeline.named_steps["kmeans"]

    #print(labels.shape)
    #print(labels[:10])
    labels=kmeans_step.labels_

    # transform the data using the pipeline
    # this is the transformed data after all preprocessing steps
    # it was a pain to get this into make_pipeline format
    X_imputed=pipeline.named_steps["simpleimputer"].transform(X)
    X_logged= pipeline.named_steps["functiontransformer"].transform(X_imputed)
    data_scaled=pipeline.named_steps["quantiletransformer"].transform(X_logged)

    df["cluster_label"] =labels
    # returns the transformed data after all preprocessing steps,labels,pipeline
    return df,data_scaled,labels,pipeline
