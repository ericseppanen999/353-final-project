import pandas as pd
import re
import os

file_path = "CHAN A 04-09.xls"
xls = pd.ExcelFile(file_path)

filename = os.path.basename(file_path)

match = re.match(r"([A-Za-z]+ [A-Za-z]) (\d{2}-\d{2})", filename)

if match:
    employee_name = match.group(1)
    month_year = match.group(2)
else:
    employee_name = "Unknown Employee"
    month_year = "Unknown Date"

print(f"Employee Name (from filename): {employee_name}")
print(f"Month/Year (from filename): {month_year}")

df = pd.read_excel(xls, sheet_name="Sheet1", header=None, dtype=str)
df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

project_row_index = df[df.iloc[:, 0].str.contains("PROJECT", na=False, case=False)].index

if project_row_index.empty:
    print("ERROR: 'PROJECT' header not found. Sheet format might be different.")
    exit()

start_row = project_row_index[0] + 2

timecard_data = df.iloc[start_row:].copy()
timecard_data.dropna(axis=1, how="all", inplace=True)

stop_keywords = ["subtotal", "total", "WORK CODES", "STAT. HOLIDAY", "ADMIN /GENERAL", "VACATION"]
stop_row_index = timecard_data[timecard_data.iloc[:, 0].str.contains('|'.join(stop_keywords), na=False, case=False)].index

if not stop_row_index.empty:
    stop_row = stop_row_index[0]
    timecard_data = timecard_data.iloc[:stop_row]

timecard_data = timecard_data[timecard_data.iloc[:, 0].str.match(r"^\d+$", na=False)]

num_columns = len(timecard_data.columns)
columns = ["Project No", "Project Name", "Work Code"] + list(range(1, num_columns - 4)) + ["Total Hours", "Comments"]
columns = columns[:num_columns]
timecard_data.columns = columns

timecard_data["Total Hours"] = pd.to_numeric(timecard_data["Total Hours"], errors="coerce")
total_hours_worked = timecard_data["Total Hours"].sum()

print(f"Total Hours Worked by {employee_name} in {month_year}: {total_hours_worked}")

file_safe_name = employee_name.replace(' ', '_').replace('/', '_')
file_safe_month = month_year.replace(' ', '_').replace('/', '_')

timecard_output = f"{file_safe_name}_{file_safe_month}_timesheet.csv"
timecard_data.to_csv(timecard_output, index=False)

print(f"Timecard data saved to {timecard_output}")
