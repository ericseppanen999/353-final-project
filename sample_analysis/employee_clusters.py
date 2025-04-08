import sqlite3
import pandas as pd
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
import matplotlib.pyplot as plt

db_path = "timekeeping.db"
conn = sqlite3.connect(db_path)

query = """
SELECT 
    e.employee_id, 
    e.name,
    SUM(t.hours_worked) AS total_hours,
    COUNT(DISTINCT t.date) AS days_worked,
    COUNT(DISTINCT t.project_no) AS projects_count
FROM time_entries t
JOIN employees e ON t.employee_id = e.employee_id
GROUP BY e.employee_id, e.name;
"""

df = pd.read_sql_query(query, conn)
conn.close()

df['avg_hours_per_day'] = df['total_hours'] / df['days_worked']

df['avg_hours_per_day'] = df['avg_hours_per_day'].replace([np.inf, -np.inf], np.nan)

features = df[['total_hours', 'days_worked', 'projects_count', 'avg_hours_per_day']]

pipeline = make_pipeline(
    SimpleImputer(strategy='mean'),
    StandardScaler(),
    PCA(n_components=2)
)

X_pca = pipeline.fit_transform(features)

k = 3 
kmeans = KMeans(n_clusters=k, random_state=42)
clusters = kmeans.fit_predict(X_pca)
df['cluster'] = clusters

# ----- Visualize Clusters -----
plt.figure(figsize=(10, 6))
scatter = plt.scatter(X_pca[:, 0], X_pca[:, 1], c=df['cluster'], cmap='viridis', s=100, alpha=0.8)
plt.xlabel("PCA Component 1")
plt.ylabel("PCA Component 2")
plt.title("Employee Clustering Based on Time Entries")
plt.colorbar(scatter, label='Cluster')
plt.show()

print(df[['employee_id', 'name', 'total_hours', 'days_worked', 'projects_count', 'avg_hours_per_day', 'cluster']])
