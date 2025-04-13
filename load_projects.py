import sqlite3
import pandas as pd
import numpy as np
import os
import re
import sys
import glob
import logging
from datetime import datetime

logging.basicConfig(
    filename='missing_projects.log',
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)
def parse_filename(filename):
    valid_months = {
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december"
    }
    base = os.path.basename(filename)
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

def clean_project_no(project_no):
    project_no = str(project_no).strip()
    project_no = re.sub(r'^[0]+', '', project_no)
    return project_no
db_path = 'timekeeping.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS projects")
cur.execute("DROP TABLE IF EXISTS financial_data")
conn.commit()

cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        project_no TEXT PRIMARY KEY,
        project_name TEXT NOT NULL,
        project_captain TEXT NOT NULL,
        developer TEXT,
        neighbourhood TEXT
    );
""")
conn.commit()
cur.execute("""
    CREATE TABLE IF NOT EXISTS financial_data (
        project_no TEXT PRIMARY KEY,
        percent_complete REAL,
        fee_earned_to_date REAL,
        fee_as_per_contract REAL,
        amount_left_to_bill REAL,
        target_fees_per_hour REAL,
        actual_fees_per_hour REAL,
        pre_CA_budget_hours REAL,
        pre_CA_actual_hours REAL,
        hours_left REAL,
        months_in_construction REAL,
        construction_fee_per_month REAL,
        CA_actual_hours REAL,
        CA_budget_hours REAL,
        date_updated TEXT,
        classification TEXT,
        storeys TEXT,
        construction_type TEXT,
        floor_area REAL,
        cost_per_sq_ft REAL,
        construction_budget REAL,
        number_of_units INTEGER,
        corrected_fee_budget_hours REAL,
        corrected_fee_actual_hours REAL,
        fee_per_unit_based_on_higher_fee_value REAL,
        fee_per_sf_based_on_higher_fee_value REAL,
        fee_construction_budget REAL,
        corrected_fee_construction_budget REAL
    );
""")
conn.commit()

project_data=pd.read_excel('Project_Data/Project_Archive_List.xls', sheet_name='Sheet1', skiprows=1)
financial_data=pd.read_excel('Project_Data/Financial_Data.xls', sheet_name='Sheet1', skiprows=1)

project_data=pd.DataFrame(project_data)
financial_data=pd.DataFrame(financial_data)

project_data = project_data[['Project No.', 'Project Name', 'Team Lead', 'Developer', 'AHJ/ Neighbourhood']]
project_data.columns = ['project_no', 'project_name', 'project_captain', 'developer', 'neighbourhood']
project_data = project_data.dropna(subset=['project_no'])
project_data = project_data[~project_data[['project_name', 'project_captain', 'developer', 'neighbourhood']].isna().all(axis=1)]
project_data['project_no'] = project_data['project_no'].apply(clean_project_no)
project_tuples = list(project_data[['project_no','project_name','project_captain','developer','neighbourhood']].itertuples(index=False, name=None))
cur.executemany('''
    INSERT OR IGNORE INTO projects (project_no, project_name, project_captain, developer, neighbourhood)
    VALUES (?,?,?,?,?)
''', project_tuples)
conn.commit()
financial_data.columns = financial_data.columns.str.strip()
cols = [
    "Job Number", "Job Name", "Job Captain", "% Complete", "Fee Earned to Date", 
    "Fee as per Contract", "Amount Left to be Billed", "Target Fees per Hour", 
    "Actual Fees per Hour", "Budget Hours", "Actual Hours", "Hours Left", 
    "Months in Construction", "Construction Fee Per Month", "Actual Hours", 
    "Budget Hours", "Date Updated", "Classification", "Storeys", "Const Type", 
    "Floor Area (sf)", "Cost per sq. ft.", "Construction Budget", "Number of units", 
    "Corrected Fee (Budget Hours)", "Corrected Fee (Actual Hours)", 
    "Fee per unit based on higher Fee Value", "Fee per s.f. based on higher Fee Value", 
    "Fee/ Construction Budget", "Corrected Fee/Construction Budget"
]
financial_data = financial_data[cols]
financial_data.columns = [
    "project_no", "project_name", "project_captain", "percent_complete", "fee_earned_to_date",
    "fee_as_per_contract", "amount_left_to_bill", "target_fees_per_hour",
    "actual_fees_per_hour", "pre_CA_budget_hours", "pre_CA_actual_hours", "hours_left",
    "months_in_construction", "construction_fee_per_month", "CA_actual_hours", "CA_budget_hours",
    "date_updated", "classification", "storeys", "construction_type",
    "floor_area", "cost_per_sq_ft", "construction_budget", "number_of_units",
    "corrected_fee_budget_hours", "corrected_fee_actual_hours",
    "fee_per_unit_based_on_higher_fee_value", "fee_per_sf_based_on_higher_fee_value",
    "fee_construction_budget", "corrected_fee_construction_budget"
]

financial_data['project_no'] = financial_data['project_no'].astype(str).apply(clean_project_no)

financial_tuples = list(financial_data[['project_no','percent_complete','fee_earned_to_date',
    'fee_as_per_contract','amount_left_to_bill','target_fees_per_hour','actual_fees_per_hour',
    'pre_CA_budget_hours','pre_CA_actual_hours','hours_left','months_in_construction',
    'construction_fee_per_month','CA_actual_hours','CA_budget_hours','date_updated',
    'classification','storeys','construction_type','floor_area','cost_per_sq_ft',
    'construction_budget','number_of_units','corrected_fee_budget_hours',
    'corrected_fee_actual_hours','fee_per_unit_based_on_higher_fee_value',
    'fee_per_sf_based_on_higher_fee_value','fee_construction_budget','corrected_fee_construction_budget'
]].itertuples(index=False, name=None))

cur.executemany('''
    INSERT OR IGNORE INTO financial_data (
        project_no, percent_complete, fee_earned_to_date,
        fee_as_per_contract, amount_left_to_bill, target_fees_per_hour, actual_fees_per_hour,
        pre_CA_budget_hours, pre_CA_actual_hours, hours_left, months_in_construction, construction_fee_per_month,
        CA_actual_hours, CA_budget_hours, date_updated, classification, storeys, construction_type,
        floor_area, cost_per_sq_ft, construction_budget, number_of_units, corrected_fee_budget_hours,
        corrected_fee_actual_hours, fee_per_unit_based_on_higher_fee_value, fee_per_sf_based_on_higher_fee_value,
        fee_construction_budget, corrected_fee_construction_budget
    )
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
''', financial_tuples)
conn.commit()

conn.close()

print("processing projects complete")
