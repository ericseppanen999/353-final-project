import sqlite3
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.pipeline import make_pipeline


# load annual usage data from database
def load_annual_usage(db_path="../timekeeping.db"):
    conn=sqlite3.connect(db_path)
    billable=pd.read_sql("""SELECT e.employee_id,e.name,e.position,SUM(t.hours_worked) AS billable_hours
        FROM time_entries t JOIN employees e USING(employee_id) GROUP BY e.employee_id""",conn)
    nonbill=pd.read_sql("""SELECT n.employee_id,SUM(n.hours_worked) AS non_billable_hours
        FROM non_billable_entries n GROUP BY n.employee_id""",conn)
    conn.close()

    # merge billable and non-billable data
    # outer join to include all employees?????
    df=pd.merge(billable,nonbill,on="employee_id",how="outer").fillna(0)
    df['total_hours']=df['billable_hours']+df['non_billable_hours']
    df['total_hours']=df['total_hours'].replace(0,1) # div by zero
    df['billable_pct']=df['billable_hours']/df['total_hours']
    df['non_billable_pct']=df['non_billable_hours']/df['total_hours']
    df["is_senior"]=df["position"].str.contains("Senior|Principal",na=False).astype(int)
    return df

# cluster data into groups
def cluster_data(df,n_clusters=3):
    df['log_total_hours']=np.log1p(df['total_hours'])
    X =df[['billable_pct','log_total_hours']]
    #print(X.shape)
    pipeline=make_pipeline(
        StandardScaler(),
        KMeans(n_clusters=n_clusters)
    )
    # fit and predict
    #pipeline.fit(X)
    # add cluster labels to original dataframe
    df['cluster']=pipeline.fit_predict(X)
    # return kmeans model
    km=pipeline.steps[-1][1]
    return df,km