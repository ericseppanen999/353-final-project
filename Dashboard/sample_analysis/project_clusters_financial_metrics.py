import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

# Connect to the database and load financial_data
conn = sqlite3.connect("timekeeping.db")
df_fin = pd.read_sql_query("SELECT * FROM financial_data", conn)
conn.close()

for col in ['percent_complete', 'fee_earned_to_date', 'fee_as_per_contract', 
            'pre_CA_budget_hours', 'pre_CA_actual_hours', 'months_in_construction']:
    df_fin[col] = pd.to_numeric(df_fin[col], errors='coerce')

df_fin['fee_variance'] = df_fin['fee_as_per_contract'] - df_fin['fee_earned_to_date']
df_fin['hours_variance'] = df_fin['pre_CA_budget_hours'] - df_fin['pre_CA_actual_hours']

features = df_fin[['percent_complete', 'fee_variance', 'hours_variance', 'months_in_construction']].dropna()

pipeline = make_pipeline(StandardScaler(), PCA(n_components=2))
X_pca = pipeline.fit_transform(features)

k = 3
kmeans = KMeans(n_clusters=k, random_state=42)
features['cluster'] = kmeans.fit_predict(X_pca)

plt.figure(figsize=(10, 6))
scatter = plt.scatter(X_pca[:, 0], X_pca[:, 1], c=features['cluster'], cmap='viridis', s=80, alpha=0.8)
plt.xlabel("PCA Component 1")
plt.ylabel("PCA Component 2")
plt.title("Project Clustering by Financial Metrics")
plt.colorbar(scatter, label='Cluster')
plt.show()

cluster_summary = features.groupby('cluster').mean()
print("Cluster Summary:")
print(cluster_summary)
