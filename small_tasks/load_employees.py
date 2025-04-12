import pandas as pd
import sqlite3


# master employee list

employee_list=pd.read_excel('Staff Chargeout Matrix.xlsx',sheet_name='employees')
billable_dict={
    "Principal": 205,
    "Project Arch/Proj Man": 165,
    "Contractor Administrator": 145,
    "Senior Designer/Architect/Project Coordinator": 135,
    "Int Designer/Tech": 120,
    "Junior Design Assist/Tech": 95,
    "Admin Staff": 65
}

linked_dict={
    "A":"Principal",
    "B":"Project Arch/Proj Man",
    "C":"Contractor Administrator",
    "D":"Senior Designer/Architect/Project Coordinator",
    "E":"Int Designer/Tech",
    "F":"Junior Design Assist/Tech",
    "G":"Admin Staff"
}

def get_billable_rate(code):
    if code in linked_dict:
        return billable_dict[linked_dict[code]]
    else:
        return None


df=pd.DataFrame(employee_list)
df['billable_rate']=df['Code'].apply(get_billable_rate)
df['billable_rate'].fillna(0,inplace=True)
df['billable_rate']=df['billable_rate'].astype(int)

conn=sqlite3.connect('timekeeping.db')

