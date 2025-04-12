import sqlite3
import pandas as pd


conn=sqlite3.connect('timekeeping.db')
cur=conn.cursor()

query="""
SELECT * FROM employees
"""
df=pd.read_sql_query(query,conn)
conn.close()

df.to_csv('employees.csv', index=False)