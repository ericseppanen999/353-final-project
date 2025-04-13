import sqlite3
import pandas as pd
import numpy as np
import os
import re
import sys
import glob
import logging
from datetime import datetime
import difflib

# configure logging
logging.basicConfig(filename='missing_projects.log',level=logging.WARNING,format='%(asctime)s - %(levelname)s - %(message)s',filemode='a')

# validate and parse command line arguments
if len(sys.argv)<3:
    print("Usage: python scriptname.py <start_year> <end_year>")
    sys.exit(1)

try:
    min_year=int(sys.argv[1])
    max_year=int(sys.argv[2])
except ValueError:
    print("Error: Start and end year must be integers.")
    sys.exit(1)

if not (2003<=min_year<=2025) or not (2003<=max_year<=2025):
    print("Error: Years must be between 2003 and 2024.")
    sys.exit(1)

if min_year>max_year:
    print("Error: Start year must be less than or equal to end year.")
    sys.exit(1)

# helper: revised filename parser
def parse_filename(filename):
    valid_months={"january","february","march","april","may","june","july","august","september","october","november","december"}
    base=os.path.basename(filename)
    base=re.sub(r'(_(projects|summary))?\.xls(x)?$', '', base, flags=re.IGNORECASE)
    base=re.sub(r'(_(projects|summary))?\.csv$', '', base, flags=re.IGNORECASE)
    parts=base.split('_')
    if len(parts)>=3:
        candidate=parts[-2].lower()
        if candidate in valid_months:
            employee_name=" ".join(parts[:-2])
            month_year=parts[-2]+" "+parts[-1]
        else:
            try:
                month_num=int(candidate)
                if 1<=month_num<=12:
                    employee_name=" ".join(parts[:-2])
                    month_name=datetime(1900,month_num,1).strftime("%B")
                    month_year=month_name+" "+parts[-1]
                else:
                    employee_name=" ".join(parts[:-1])
                    month_year=parts[-1]
            except ValueError:
                employee_name=" ".join(parts[:-1])
                month_year=parts[-1]
    else:
        employee_name="Unknown"
        month_year="Unknown"
    return (employee_name.strip(),month_year.strip())

def id_hash(employee_name):
    return hash(employee_name)%1000000

# updated clean_project_no
def clean_project_no(project_no):
    s=str(project_no).strip()
    try:
        f=float(s)
        if f.is_integer():
            return str(int(f))
    except ValueError:
        pass
    m=re.match(r'(\d+)',s)
    if m:
        return m.group(1)
    else:
        return s

def drop_tables_if_exists(db_path):
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute("DROP TABLE IF EXISTS employees")
    cur.execute("DROP TABLE IF EXISTS time_entries")
    cur.execute("DROP TABLE IF EXISTS non_billable_entries")
    conn.commit()
    conn.close()
    print("Tables dropped successfully (employees,time_entries,non_billable_entries).")

# helper: get matching employee using difflib
def get_matching_employee(parsed_name,master_names,cutoff=0.8):
    if parsed_name in master_names:
        return parsed_name
    matches=difflib.get_close_matches(parsed_name,master_names,n=1,cutoff=cutoff)
    return matches[0] if matches else None

def load_master_employees(db_path,master_file):
    df=pd.read_excel(master_file,sheet_name='employees')
    df['Code']=df['Code'].astype(str).str.strip().str.upper()
    rate_mapping={"A":205,"B":165,"C":145,"D":135,"E":120,"F":95,"G":65}
    linked_dict={"A":"Principal","B":"Project Arch/Proj Man","C":"Contractor Administrator","D":"Senior Designer/Architect/Project Coordinator","E":"Int Designer/Tech","F":"Junior Design Assist/Tech","G":"Admin Staff"}
    df['billable_rate']=df['Code'].map(rate_mapping)
    df['billable_rate']=df['billable_rate'].fillna(0).astype(int)
    df['position']=df['Code'].map(linked_dict)
    df['Name']=df['Name'].astype(str).str.strip()
    df=df[df['Name']!=""]
    master_employees={}
    for idx,row in df.iterrows():
        name=row['Name']
        employee_id=id_hash(name)
        master_employees[name]=employee_id
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            employee_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            billable_rate INTEGER,
            position TEXT)""")
    
    for name,employee_id in master_employees.items():
        employee_rates=df.loc[df['Name']==name,'billable_rate']
        if employee_rates.empty:
            print(f"Warning: Billable rate not found for employee '{name}', setting to 0")
            rate=0
        else:
            rate=employee_rates.iloc[0]
            try:
                rate=int(rate)
            except ValueError:
                print(f"Warning: Invalid billable rate for employee '{name}', setting to 0")
                rate=0
        employee_positions=df.loc[df['Name']==name,'position']
        if employee_positions.empty:
            pos=""
        else:
            pos=employee_positions.iloc[0]
        cur.execute("INSERT OR IGNORE INTO employees(employee_id,name,billable_rate,position) VALUES(?,?,?,?)",(employee_id,name,rate,pos))
    conn.commit()
    conn.close()
    print("Master employees loaded into database.")
    return master_employees

def load_projects_csv_to_db(csv_file,db_path,master_employees):
    employee_name,month_year=parse_filename(csv_file)
    print(f"[Projects] Parsed from filename: Employee = '{employee_name}', Month/Year = {month_year}")
    matched_employee=get_matching_employee(employee_name,master_employees.keys())
    if not matched_employee:
        msg=f"Employee '{employee_name}' from file {csv_file} not found in master list. Skipping file."
        logging.error(msg)
        print(msg)
        return
    elif matched_employee!=employee_name:
        print(f"Using close match: '{matched_employee}' for employee '{employee_name}'.")
        employee_name=matched_employee
    employee_id=master_employees[employee_name]
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_time_entries_employee_date ON time_entries(employee_id,date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_time_entries_project_date ON time_entries(project_no,date)")
    conn.commit()
    df=pd.read_csv(csv_file)
    for idx,row in df.iterrows():
        raw_project_no=row["PROJECT NO"]
        cleaned_project_no=clean_project_no(raw_project_no)
        if cleaned_project_no=="":
            print(f"Skipping row {idx} due to invalid project number: {raw_project_no}")
            continue
        project_name=str(row["PROJECT NAME"]).strip()
        work_code=str(row["WORK CODE"]).strip()
        cur.execute("SELECT project_no FROM projects WHERE project_no = ?",(cleaned_project_no,))
        if cur.fetchone() is None:
            msg=f"Row {idx}: Project number {cleaned_project_no} ({project_name}) not found in projects table. Skipping row."
            logging.warning(msg)
            print(msg)
            continue
        for day in range(1,32):
            col=str(day)
            try:
                hours=float(row[col])
            except (ValueError,TypeError):
                hours=0.0
            if hours>0:
                try:
                    entry_date=datetime.strptime(f"{day} {month_year}","%d %B %Y").date()
                except Exception as e:
                    print(f"Error parsing date from '{month_year}' and day {day}: {e}")
                    continue
                cur.execute("""
                INSERT INTO time_entries(employee_id,project_no,work_code,date,hours_worked)
                VALUES (?,?,?,?,?)
                """,(employee_id,cleaned_project_no,work_code,entry_date.isoformat(),hours))
    conn.commit()
    conn.close()
    print(f"[Projects] Data from {csv_file} loaded into the database.")

# loader for summary csvs (non-billable hours)
def load_summary_csv_to_db(csv_file,db_path,master_employees):
    employee_name,month_year=parse_filename(csv_file)
    print(f"[Summary] Parsed from filename: Employee = '{employee_name}', Month/Year = {month_year}")
    matched_employee=get_matching_employee(employee_name,master_employees.keys())
    if not matched_employee:
        msg=f"Employee '{employee_name}' from file {csv_file} not found in master list. Skipping file."
        logging.error(msg)
        print(msg)
        return
    elif matched_employee!=employee_name:
        print(f"Using close match: '{matched_employee}' for employee '{employee_name}'.")
        employee_name=matched_employee
    employee_id=master_employees[employee_name]
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
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
    df=pd.read_csv(csv_file)
    for idx,row in df.iterrows():
        category=str(row["non-billable"]).strip()
        if "total" in category.lower():
            continue
        for day in range(1,32):
            col=str(day)
            try:
                hours=float(row[col])
            except (ValueError,TypeError):
                hours=0.0
            if hours>0:
                try:
                    entry_date=datetime.strptime(f"{day} {month_year}","%d %B %Y").date()
                except Exception as e:
                    print(f"Error parsing date from '{month_year}' and day {day}: {e}")
                    continue
                cur.execute("""
                INSERT INTO non_billable_entries(employee_id,category,date,hours_worked)
                VALUES (?,?,?,?)
                """,(employee_id,category,entry_date.isoformat(),hours))
    conn.commit()
    conn.close()
    print(f"[Summary] Data from {csv_file} loaded into the database.")

# main processing loop
input_directory="Cleaned_Timekeeping"
db_path="timekeeping.db"
master_file="Staff Chargeout Matrix.xlsx"
drop_tables_if_exists(db_path)
master_employees=load_master_employees(db_path,master_file)
project_files=[]
summary_files=[]
for year_folder in os.listdir(input_directory):
    if not year_folder.isdigit():
        continue
    year=int(year_folder)
    if year<min_year or year>max_year:
        continue
    year_path=os.path.join(input_directory,year_folder)
    if not os.path.isdir(year_path):
        continue
    for month_folder in os.listdir(year_path):
        projects_folder=os.path.join(year_path,month_folder,"Projects")
        if os.path.isdir(projects_folder):
            for file in glob.glob(os.path.join(projects_folder,"*.csv")):
                if "~$" in os.path.basename(file).lower() or "unknown" in os.path.basename(file).lower():
                    continue
                project_files.append(file)
    for month_folder in os.listdir(year_path):
        summaries_folder=os.path.join(year_path,month_folder,"Summaries")
        if os.path.isdir(summaries_folder):
            for file in glob.glob(os.path.join(summaries_folder,"*.csv")):
                if "~$" in os.path.basename(file).lower() or "unknown" in os.path.basename(file).lower():
                    continue
                summary_files.append(file)
print(f"Total project files found: {len(project_files)}")
print(f"Total summary files found: {len(summary_files)}")
for file in project_files:
    load_projects_csv_to_db(file,db_path,master_employees)
for file in summary_files:
    load_summary_csv_to_db(file,db_path,master_employees)
print("Processing complete.")
