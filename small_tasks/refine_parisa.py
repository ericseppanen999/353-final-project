import sqlite3
import pandas as pd

# Connect
conn = sqlite3.connect('timekeeping.db')
cur = conn.cursor()

# 1) Find both IDs
paria = pd.read_sql_query(
    "SELECT employee_id FROM employees WHERE name LIKE '%Paria Moghaddam%';",
    conn
)
parisa = pd.read_sql_query(
    "SELECT employee_id FROM employees WHERE name LIKE '%Parisa Moghaddam%';",
    conn
)

if paria.empty or parisa.empty:
    raise ValueError("Could not find both Paria and Parisa in employees table.")

paria_id = int(paria.employee_id.iloc[0])
parisa_id = int(parisa.employee_id.iloc[0])
print(f"Paria ID:  {paria_id}")
print(f"Parisa ID: {parisa_id}")

# 2) Reassign all time_entries for Parisa → Paria
cur.execute(
    "UPDATE time_entries SET employee_id = ? WHERE employee_id = ?;",
    (paria_id, parisa_id)
)

# 3) Reassign non_billable_entries as well (if needed)
cur.execute(
    "UPDATE non_billable_entries SET employee_id = ? WHERE employee_id = ?;",
    (paria_id, parisa_id)
)

# 4) Delete the Parisa record from employees
cur.execute(
    "DELETE FROM employees WHERE employee_id = ?;",
    (parisa_id,)
)

# 5) Commit and close
conn.commit()
conn.close()

print("Merged Parisa into Paria and removed duplicate record.")
