import pandas as pd
import sqlite3
import os
import re
from datetime import datetime

# ----- Helper: Revised filename parser -----
def parse_filename(filename):
    """
    Parse the filename to extract employee name and month/year.
    Assumes filenames are like:
      "Allan_Seppanen_May_2021_projects.csv"
    or possibly
      "Allan_Seppanen_5_2021_projects.csv"
    This function removes the trailing '_projects' and then checks if the penultimate
    token is a valid month name (or a number between 1 and 12). If so, it uses the last
    two tokens as the month and year and the rest as the employee name.
    """
    valid_months = {
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december"
    }
    
    base = os.path.basename(filename)
    # Remove suffix like "_projects.csv" or ".csv"
    base = re.sub(r'(_projects)?\.xls(x)?$', '', base, flags=re.IGNORECASE)
    base = re.sub(r'(_projects)?\.csv$', '', base, flags=re.IGNORECASE)
    parts = base.split('_')
    
    # If there are at least three parts, check if the penultimate token is a valid month.
    if len(parts) >= 3:
        candidate = parts[-2].lower()
        # Check if candidate is a valid month name or a valid month number.
        if candidate in valid_months:
            employee_name = " ".join(parts[:-2])
            month_year = parts[-2] + " " + parts[-1]
        else:
            # Check if candidate is numeric and in range 1-12.
            try:
                month_num = int(candidate)
                if 1 <= month_num <= 12:
                    employee_name = " ".join(parts[:-2])
                    # Optionally, convert numeric month to month name:
                    month_name = datetime(1900, month_num, 1).strftime("%B")
                    month_year = month_name + " " + parts[-1]
                else:
                    # Otherwise, assume last token is year.
                    employee_name = " ".join(parts[:-1])
                    month_year = parts[-1]
            except ValueError:
                # Fallback if candidate is not numeric.
                employee_name = " ".join(parts[:-1])
                month_year = parts[-1]
    else:
        employee_name = "Unknown"
        month_year = "Unknown"
    return (employee_name, month_year)

def id_hash(employee_name):
    # integer hash of the employee name
    return hash(employee_name) % 1000000


def drop_tables_if_exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS employees")
    cur.execute("DROP TABLE IF EXISTS projects")
    cur.execute("DROP TABLE IF EXISTS time_entries")
    conn.commit()
    conn.close()
    print("Tables dropped successfully.")


# ----- Database Loader Script -----
def load_csv_to_db(csv_file, db_path):
    # Parse employee info from the filename.
    employee_name, month_year = parse_filename(csv_file)
    print(f"Parsed from filename: Employee = {employee_name}, Month/Year = {month_year}")

    # Connect to the SQLite database (or create if not exists)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    

    # Create tables if not exist.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        project_no TEXT PRIMARY KEY,
        project_name TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS time_entries (
        entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        project_no TEXT,
        work_code TEXT,
        date DATE,
        hours_worked DECIMAL,
        FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
        FOREIGN KEY (project_no) REFERENCES projects(project_no)
    )
    """)
    # Create indexes.
    cur.execute("CREATE INDEX IF NOT EXISTS idx_time_entries_employee_date ON time_entries(employee_id, date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_time_entries_project_date ON time_entries(project_no, date)")
    conn.commit()

    # Insert employee if not exists.
    employee_id = id_hash(employee_name)
    cur.execute("INSERT OR IGNORE INTO employees(employee_id, name) VALUES(?, ?)", (employee_id, employee_name))
    conn.commit()
    cur.execute("SELECT employee_id FROM employees WHERE name=?", (employee_name,))
    employee_id = cur.fetchone()[0]

    # Read the CSV file.
    df = pd.read_csv(csv_file)
    # Expected columns: PROJECT NO, PROJECT NAME, WORK CODE, "1", "2", ... "31", TOTAL, DESCRIPTION / COMMENTS.
    # We'll ignore TOTAL and DESCRIPTION/COMMENTS for time entries.
    for idx, row in df.iterrows():
        project_no = str(row["PROJECT NO"]).strip()
        project_name = str(row["PROJECT NAME"]).strip()
        work_code = str(row["WORK CODE"]).strip()
        
        # Insert project row if not exists.
        cur.execute("INSERT OR IGNORE INTO projects(project_no, project_name) VALUES(?, ?)",
                    (project_no, project_name))
        # For each day column ("1" to "31").
        for day in range(1, 32):
            col = str(day)
            try:
                hours = float(row[col])
            except (ValueError, TypeError):
                hours = 0.0
            if hours > 0:
                # Construct the date.
                # Assume month_year is in the format "May 2021" (as parsed from the filename).
                try:
                    entry_date = datetime.strptime(f"{day} {month_year}", "%d %B %Y").date()
                except Exception as e:
                    print(f"Error parsing date from '{month_year}' and day {day}: {e}")
                    continue
                cur.execute("""
                INSERT INTO time_entries(employee_id, project_no, work_code, date, hours_worked)
                VALUES(?, ?, ?, ?, ?)
                """, (employee_id, project_no, work_code, entry_date.isoformat(), hours))
    conn.commit()

    # Query and print tables for verification.
    print("=== Employees Table ===")
    df_emp = pd.read_sql_query("SELECT * FROM employees", conn)
    print(df_emp)
    print("=== Projects Table ===")
    df_proj = pd.read_sql_query("SELECT * FROM projects", conn)
    print(df_proj)
    print("=== Time Entries Table ===")
    df_time = pd.read_sql_query("SELECT * FROM time_entries", conn)
    print(df_time)

    conn.close()
    print("Data loaded into the database successfully.")

# Set CSV file path.
csv_file1 = "Cleaned_Timekeeping/2021/05-21/Projects/Liam_Gilles_May_2021_projects.csv"
csv_file2 = "Cleaned_Timekeeping/2021/05-21/Projects/Allan_Seppanen_May_2021_projects.csv"
csv_file3 = "Cleaned_Timekeeping/2021/05-21/Projects/Rod_MacPherson_May_2021_projects.csv"
db_path = "timekeeping.db"

drop_tables_if_exists(db_path)
load_csv_to_db(csv_file1, db_path)
load_csv_to_db(csv_file2, db_path)
load_csv_to_db(csv_file3, db_path)
