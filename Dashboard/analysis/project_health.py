# analysis/project_clusters.py

import sqlite3
import pandas as pd
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

def load_and_cluster(k=3, db_path="../timekeeping.db"):
    """
    Load financial_data, compute fee & hour variances,
    run PCA (2 components) and KMeans clustering with k clusters.
    Returns:
      - df_proj: original features + cluster label
      - X_pca: ndarray of shape (n_samples, 2)
      - cluster_centers: ndarray of shape (k, 2)
      - summary: DataFrame of mean feature values per cluster
    """
    # Load data
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT project_no, percent_complete, fee_earned_to_date, fee_as_per_contract, pre_CA_budget_hours, pre_CA_actual_hours, months_in_construction FROM financial_data", conn)
    conn.close()

    # Numeric conversion & variance features
    for col in ['percent_complete', 'fee_earned_to_date', 'fee_as_per_contract', 'pre_CA_budget_hours', 'pre_CA_actual_hours', 'months_in_construction']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['percent_complete', 'fee_earned_to_date', 'fee_as_per_contract', 'pre_CA_budget_hours', 'pre_CA_actual_hours', 'months_in_construction'])
    df['fee_variance'] = df['fee_as_per_contract'] - df['fee_earned_to_date']
    df['hours_variance'] = df['pre_CA_budget_hours'] - df['pre_CA_actual_hours']

    # Feature matrix
    features = df[['percent_complete', 'fee_variance', 'hours_variance', 'months_in_construction']].copy()

    # PCA pipeline
    pipeline = make_pipeline(StandardScaler(), PCA(n_components=2))
    X_pca = pipeline.fit_transform(features)

    # KMeans
    kmeans = KMeans(n_clusters=k, random_state=42)
    labels = kmeans.fit_predict(X_pca)
    df['cluster'] = labels

    # Summary stats
    summary = df.groupby('cluster')[['percent_complete', 'fee_variance', 'hours_variance', 'months_in_construction']].mean().round(2)

    return df, X_pca, kmeans.cluster_centers_, summary
