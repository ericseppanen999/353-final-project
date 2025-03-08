## database schema: ##

### employees table ###

employee_id      PRIMARY KEY       unique ID for each employee
name             TEXT NOT NULL     full employee name (lastname, first initial)

### projects table ###

project_no       PRIMARY KEY       project number (already unique, so id not necessary)
project_name     TEXT NOT NULL     name of the project
other fields: i.e. budget, total cost so far maybe.

### time entries table ###

entry_id        PRIMARY KEY       unique id for each entry
employee_id     FK employees      foreign key to employees
project_no      FK projects       foreign key to projects
work_code       TEXT              type of work (dp, wd, bp,...)
date            DATE              specific work date
hours_worked    DECIMAL           hours worked in this entry

### index ###
index on time_entries(employee_id,date)
index on time_entries(project_id,date)

### query sample ###

```
SELECT E.name, sum(T.hours_worked)
FROM time_entries T JOIN employee E on E.employee_id=T.employee_id
WHERE ...
GROUP BY e.name;

SELECT P.project_name, sum(t.hours_worked)
FROM time_entries T JOIN projects P ON T.project_id=P.project_id
GROUP BY P.project_name;
```


### loading sample ###
from chatgpt using postgres
```
import pandas as pd
import psycopg2

# Connect to PostgreSQL
conn = psycopg2.connect("dbname=timesheets user=your_user password=your_password host=localhost")
cursor = conn.cursor()

# Load CSV into Pandas
df = pd.read_csv("CHAN_A_04-09_timesheet.csv")

# Insert Data
for _, row in df.iterrows():
    cursor.execute(
        "INSERT INTO time_entries (employee_id, project_id, work_code, date, hours_worked) VALUES (%s, %s, %s, %s, %s)",
        (row["employee_id"], row["project_id"], row["Work Code"], row["date"], row["Total Hours"])
    )

conn.commit()
cursor.close()
conn.close()
```

### dataset structure ###
```
root ---> year ---> month ---> employee
```


### process ###

load excel file -> clean, transform -> save into csv's -> connect to db and load.

