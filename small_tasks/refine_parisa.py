import sqlite3
import pandas as pd

conn=sqlite3.connect('timekeeping.db')
cur=conn.cursor()

paria=pd.read_sql_query("SELECT employee_id FROM employees WHERE name LIKE '%Paria Moghaddam%';",conn)
parisa=pd.read_sql_query("SELECT employee_id FROM employees WHERE name LIKE '%Parisa Moghaddam%';",conn)

if paria.empty or parisa.empty:
    raise ValueError("Could not find both Paria and Parisa in employees table.")

paria_id=int(paria.employee_id.iloc[0])
parisa_id=int(parisa.employee_id.iloc[0])
print(f"Paria ID:{paria_id}")
print(f"Parisa ID:{parisa_id}")

cur.execute("UPDATE time_entries SET employee_id=? WHERE employee_id=?;",(paria_id,parisa_id))
cur.execute("UPDATE non_billable_entries SET employee_id=? WHERE employee_id=?;",(paria_id,parisa_id))
cur.execute("DELETE FROM employees WHERE employee_id=?;",(parisa_id,))

conn.commit()
conn.close()

print("Merged Parisa into Paria and removed duplicate record.")
