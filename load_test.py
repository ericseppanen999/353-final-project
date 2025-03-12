import pandas as pd
import sqlite3
import os
import re
import glob
from datetime import datetime

# ----- Helper: Revised filename parser -----
def parse_filename(filename):
    """
    Parse the filename to extract employee name and month/year.
    Assumes filenames are like:
      "Allan_Seppanen_May_2021_projects.csv" or
      "Vanessa_Tam_December_2024_summary.csv"
    This function removes the trailing '_projects' or '_summary' and then checks if the penultimate
    token is a valid month name (or a number between 1 and 12). If so, it uses the last two tokens
    as the month and year and the rest as the employee name.
    """
    valid_months = {
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december"
    }
    
    base = os.path.basename(filename)
    # Remove suffix like "_projects.csv", "_summary.csv", etc.
    base = re.sub(r'(_(projects|summary))?\.xls(x)?$', '', base, flags=re.IGNORECASE)
    base = re.sub(r'(_(projects|summary))?\.csv$', '', base, flags=re.IGNORECASE)
    parts = base.split('_')
    
    if len(parts) >= 3:
        candidate = parts[-2].lower()
        if candidate in valid_months:
            employee_name = " ".join(parts[:-2])
            month_year = parts[-2] + " " + parts[-1]
        else:
            try:
                month_num = int(candidate)
                if 1 <= month_num <= 12:
                    employee_name = " ".join(parts[:-2])
                    month_name = datetime(1900, month_num, 1).strftime("%B")
                    month_year = month_name + " " + parts[-1]
                else:
                    employee_name = " ".join(parts[:-1])
                    month_year = parts[-1]
            except ValueError:
                employee_name = " ".join(parts[:-1])
                month_year = parts[-1]
    else:
        employee_name = "Unknown"
        month_year = "Unknown"
    return (employee_name, month_year)

def id_hash(employee_name):
    # Compute a stable integer hash for the employee name.
    return hash(employee_name) % 1000000

def clean_project_no(project_no):
    """
    Remove all non-digit characters and leading zeros.
    Convert to integer.
    """
    # Remove any characters that are not digits.
    digits = re.sub(r'\D', '', str(project_no))
    if not digits:
        return None
    # Convert to integer to remove any leading zeros.
    return int(digits)

def drop_tables_if_exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS employees")
    cur.execute("DROP TABLE IF EXISTS projects")
    cur.execute("DROP TABLE IF EXISTS time_entries")
    cur.execute("DROP TABLE IF EXISTS non_billable_entries")
    conn.commit()
    conn.close()
    print("Tables dropped successfully.")

# ----- Loader for Project CSVs (Billable Hours) -----
def load_projects_csv_to_db(csv_file, db_path):
    employee_name, month_year = parse_filename(csv_file)
    print(f"[Projects] Parsed from filename: Employee = {employee_name}, Month/Year = {month_year}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        employee_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE
    )
    """)
    # Store project_no as INTEGER.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        project_no INTEGER PRIMARY KEY,
        project_name TEXT NOT NULL
    )
    """)
    # Store project_no as INTEGER.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS time_entries (
        entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        project_no INTEGER,
        work_code TEXT,
        date DATE,
        hours_worked DECIMAL,
        FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
        FOREIGN KEY (project_no) REFERENCES projects(project_no)
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_time_entries_employee_date ON time_entries(employee_id, date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_time_entries_project_date ON time_entries(project_no, date)")
    conn.commit()

    employee_id = id_hash(employee_name)
    cur.execute("INSERT OR IGNORE INTO employees(employee_id, name) VALUES(?, ?)", (employee_id, employee_name))
    conn.commit()
    cur.execute("SELECT employee_id FROM employees WHERE name=?", (employee_name,))
    employee_id = cur.fetchone()[0]

    df = pd.read_csv(csv_file)
    # Expected columns: PROJECT NO, PROJECT NAME, WORK CODE, "1", ... "31", TOTAL, DESCRIPTION / COMMENTS.
    for idx, row in df.iterrows():
        raw_project_no = row["PROJECT NO"]
        cleaned_project_no = clean_project_no(raw_project_no)
        if cleaned_project_no is None:
            print(f"Skipping row {idx} due to invalid project number: {raw_project_no}")
            continue
        
        project_name = str(row["PROJECT NAME"]).strip()
        work_code = str(row["WORK CODE"]).strip()
        
        cur.execute("INSERT OR IGNORE INTO projects(project_no, project_name) VALUES(?, ?)",
                    (cleaned_project_no, project_name))
        for day in range(1, 32):
            col = str(day)
            try:
                hours = float(row[col])
            except (ValueError, TypeError):
                hours = 0.0
            if hours > 0:
                try:
                    entry_date = datetime.strptime(f"{day} {month_year}", "%d %B %Y").date()
                except Exception as e:
                    print(f"Error parsing date from '{month_year}' and day {day}: {e}")
                    continue
                cur.execute("""
                INSERT INTO time_entries(employee_id, project_no, work_code, date, hours_worked)
                VALUES(?, ?, ?, ?, ?)
                """, (employee_id, cleaned_project_no, work_code, entry_date.isoformat(), hours))
    conn.commit()
    conn.close()
    print(f"[Projects] Data from {csv_file} loaded into the database.")

# ----- Loader for Summary CSVs (Non-Billable Hours) -----
def load_summary_csv_to_db(csv_file, db_path):
    employee_name, month_year = parse_filename(csv_file)
    print(f"[Summary] Parsed from filename: Employee = {employee_name}, Month/Year = {month_year}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS non_billable_entries (
        entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        category TEXT,
        date DATE,
        hours_worked DECIMAL,
        FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
    )
    """)
    conn.commit()

    employee_id = id_hash(employee_name)
    cur.execute("INSERT OR IGNORE INTO employees(employee_id, name) VALUES(?, ?)", (employee_id, employee_name))
    conn.commit()
    cur.execute("SELECT employee_id FROM employees WHERE name=?", (employee_name,))
    employee_id = cur.fetchone()[0]

    df = pd.read_csv(csv_file)
    # The summary CSV is expected to have a column "non-billable" plus columns "1" to "31" for day-wise non-billable hours.
    for idx, row in df.iterrows():
        category = str(row["non-billable"]).strip()
        if "total" in category.lower():
            continue
        for day in range(1, 32):
            col = str(day)
            try:
                hours = float(row[col])
            except (ValueError, TypeError):
                hours = 0.0
            if hours > 0:
                try:
                    entry_date = datetime.strptime(f"{day} {month_year}", "%d %B %Y").date()
                except Exception as e:
                    print(f"Error parsing date from '{month_year}' and day {day}: {e}")
                    continue
                cur.execute("""
                INSERT INTO non_billable_entries(employee_id, category, date, hours_worked)
                VALUES(?, ?, ?, ?)
                """, (employee_id, category, entry_date.isoformat(), hours))
    conn.commit()
    conn.close()
    print(f"[Summary] Data from {csv_file} loaded into the database.")

# ----- Main Loop -----
input_directory = "Cleaned_Timekeeping"
db_path = "timekeeping.db"
min_year = 2024
max_year = 2024

drop_tables_if_exists(db_path)

project_files = []
summary_files = []

# Gather all CSV files from Cleaned_Timekeeping/<year>/<month>/Projects/ and /Summaries/
for year_folder in os.listdir(input_directory):
    if not year_folder.isdigit():
        continue
    year = int(year_folder)
    if year < min_year or year > max_year:
        continue
    year_path = os.path.join(input_directory, year_folder)
    if not os.path.isdir(year_path):
        continue
    # Projects
    for month_folder in os.listdir(year_path):
        projects_folder = os.path.join(year_path, month_folder, "Projects")
        if os.path.isdir(projects_folder):
            for file in glob.glob(os.path.join(projects_folder, "*.csv")):
                if "~$" in os.path.basename(file).lower() or "unknown" in os.path.basename(file).lower():
                    continue
                project_files.append(file)
    # Summaries
    for month_folder in os.listdir(year_path):
        summaries_folder = os.path.join(year_path, month_folder, "Summaries")
        if os.path.isdir(summaries_folder):
            for file in glob.glob(os.path.join(summaries_folder, "*.csv")):
                if "~$" in os.path.basename(file).lower() or "unknown" in os.path.basename(file).lower():
                    continue
                summary_files.append(file)

print(f"Total project files found: {len(project_files)}")
print(f"Total summary files found: {len(summary_files)}")

for file in project_files:
    load_projects_csv_to_db(file, db_path)

for file in summary_files:
    load_summary_csv_to_db(file, db_path)

# ----- Print Tables at the End -----
conn = sqlite3.connect(db_path)
print("\n=== Employees Table ===")
df_emp = pd.read_sql_query("SELECT * FROM employees", conn)
print(df_emp)
print("\n=== Projects Table ===")
df_proj = pd.read_sql_query("SELECT * FROM projects", conn)
print(df_proj)
print("\n=== Time Entries Table ===")
df_time = pd.read_sql_query("SELECT * FROM time_entries", conn)
print(df_time)
print("\n=== Non-Billable Entries Table ===")
df_nb = pd.read_sql_query("SELECT * FROM non_billable_entries", conn)
print(df_nb)

# Example: Top 5 Projects by total billable hours.
df_top_proj = pd.read_sql_query("""
    SELECT T.project_no, P.project_name, SUM(T.hours_worked) AS total_hours
    FROM time_entries T
    JOIN projects P ON T.project_no = P.project_no
    GROUP BY T.project_no
    ORDER BY total_hours DESC
""", conn)
print("\n=== Top 5 Projects by Hours ===")
print(df_top_proj)
df_top_proj.to_csv("top_projects.csv", index=False)
print("\nTop projects data has been written to 'top_projects.csv'.")

# Example: Top 5 Employees by total hours (billable + non-billable).
df_top_emp = pd.read_sql_query("""
    SELECT E.name, SUM(T.hours_worked) AS total_hours
    FROM time_entries T
    JOIN employees E ON T.employee_id = E.employee_id
    GROUP BY E.name
    ORDER BY total_hours DESC
    LIMIT 10
""", conn)

df_top_nonbillable = pd.read_sql_query("""
    SELECT E.name, SUM(N.hours_worked) AS total_hours
    FROM non_billable_entries N
    JOIN employees E ON N.employee_id = E.employee_id
    GROUP BY E.name
    ORDER BY total_hours DESC
    LIMIT 10
""", conn)

print("\n=== Top 5 Employees by Hours ===")
print(df_top_emp)

print("\n=== Top 5 Employees by Non-Billable Hours ===")
print(df_top_nonbillable)

conn.close()
