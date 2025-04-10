import pandas as pd
import sqlite3

def query_employees(conn):
    df=pd.read_sql_query("SELECT * FROM employees",conn)
    print("=== Employees Table ===")
    print(df)

def query_projects(conn):
    df=pd.read_sql_query("SELECT * FROM projects",conn)
    print("\n=== Projects Table ===")
    print(df)

def query_time_entries(conn):
    df=pd.read_sql_query("SELECT * FROM time_entries",conn)
    print("\n=== Time Entries Table ===")
    print(df)

def query_nonbillable_entries(conn):
    df=pd.read_sql_query("SELECT * FROM non_billable_entries",conn)
    print("\n=== Non-Billable Entries Table ===")
    print(df)

def query_top_projects(conn):
    query="""
    SELECT T.project_no,P.project_name,SUM(T.hours_worked) AS total_hours
    FROM time_entries T
    JOIN projects P ON T.project_no=P.project_no
    GROUP BY T.project_no
    ORDER BY total_hours DESC
    """
    df=pd.read_sql_query(query,conn)
    print("\n=== Top 5 Projects by Total Billable Hours ===")
    print(df)
    df.to_csv('top_projects.csv',index=False) # export to csv

def query_top_employees(conn):
    query_billable="""
    SELECT E.name,SUM(T.hours_worked) AS total_billable_hours
    FROM time_entries T
    JOIN employees E ON T.employee_id=E.employee_id
    GROUP BY E.name
    """
    query_nonbillable="""
    SELECT E.name,SUM(N.hours_worked) AS total_nonbillable_hours
    FROM non_billable_entries N
    JOIN employees E ON N.employee_id=E.employee_id
    GROUP BY E.name
    """
    df_billable=pd.read_sql_query(query_billable,conn)
    df_nonbillable=pd.read_sql_query(query_nonbillable,conn)
    df=pd.merge(df_billable,df_nonbillable,on="name",how="outer").fillna(0) # merge data
    df["total_hours"]=df["total_billable_hours"]+df["total_nonbillable_hours"]
    df=df.sort_values("total_hours",ascending=False).head(5)
    print("\n=== Top 5 Employees by Total Hours (Billable + Non-Billable) ===")
    print(df)

def query_hours_by_employee_and_month(conn):
    query="""
    SELECT E.name,strftime('%Y-%m',T.date) AS month,SUM(T.hours_worked) as billable_hours
    FROM time_entries T
    JOIN employees E ON T.employee_id=E.employee_id
    GROUP BY E.name,month
    ORDER BY month,billable_hours DESC
    """
    df=pd.read_sql_query(query,conn)
    print("\n=== Billable Hours by Employee and Month ===")
    print(df)

def query_billable_vs_nonbillable_by_employee(conn):
    query="""
    SELECT E.name,
           IFNULL(B.total_billable,0) as total_billable,
           IFNULL(N.total_nonbillable,0) as total_nonbillable,
           (IFNULL(B.total_billable,0)+IFNULL(N.total_nonbillable,0)) as total_hours
    FROM employees E
    LEFT JOIN (
        SELECT employee_id,SUM(hours_worked) as total_billable
        FROM time_entries
        GROUP BY employee_id
    ) B ON E.employee_id=B.employee_id
    LEFT JOIN (
        SELECT employee_id,SUM(hours_worked) as total_nonbillable
        FROM non_billable_entries
        GROUP BY employee_id
    ) N ON E.employee_id=N.employee_id
    ORDER BY total_hours DESC
    """
    df=pd.read_sql_query(query,conn)
    print("\n=== Billable vs Non-Billable Hours by Employee ===")
    print(df)

def query_top_projects_by_month(conn):
    query="""
    SELECT strftime('%Y-%m',date) as month,project_no,SUM(hours_worked) as total_hours
    FROM time_entries
    GROUP BY month,project_no
    ORDER BY total_hours DESC
    LIMIT 10
    """
    df=pd.read_sql_query(query,conn)
    print("\n=== Project Hours by Month (sorted by month then hours) ===")
    print(df)

def query_avg_daily_hours_by_employee(conn):
    query="""
    SELECT E.name,AVG(daily_hours) as avg_daily_hours
    FROM (
        SELECT employee_id,date,SUM(hours_worked) as daily_hours
        FROM time_entries
        GROUP BY employee_id,date
    ) AS daily
    JOIN employees E ON daily.employee_id=E.employee_id
    GROUP BY E.name
    ORDER BY avg_daily_hours DESC
    """
    df=pd.read_sql_query(query,conn)
    print("\n=== Average Daily Billable Hours by Employee ===")
    print(df)

def query_highest_daily_hours(conn):
    query="""
    SELECT E.name,date,SUM(hours_worked) as daily_hours
    FROM time_entries T
    JOIN employees E ON T.employee_id=E.employee_id
    GROUP BY T.employee_id,date
    ORDER BY daily_hours DESC
    LIMIT 5
    """
    df=pd.read_sql_query(query,conn)
    print("\n=== Top 5 Days with Highest Billable Hours per Employee ===")
    print(df)

def test(conn):
    query="""
    SELECT *
    FROM time_entries T JOIN employees E on T.employee_id=E.employee_id
    WHERE E.name='Sophie Vanasse' AND T.date='2021-02-17'
    """
    df=pd.read_sql_query(query,conn)
    print("\n=== Test ===")
    print(df)

def query_common_work_codes(conn):
    query="""
    SELECT work_code,COUNT(*) as frequency,SUM(hours_worked) as total_hours
    FROM time_entries
    GROUP BY work_code
    ORDER BY total_hours DESC
    """
    df=pd.read_sql_query(query,conn)
    print("\n=== Common Work Codes in Billable Hours ===")
    print(df)

def query_company_monthly_trend(conn):
    query="""
    SELECT strftime('%Y-%m',date) as month,SUM(hours_worked) as total_hours
    FROM (
        SELECT date,hours_worked FROM time_entries
        UNION ALL
        SELECT date,hours_worked FROM non_billable_entries
    )
    GROUP BY month
    ORDER BY month
    """
    df=pd.read_sql_query(query,conn)
    print("\n=== Company Monthly Trend (Total Hours) ===")
    print(df)

def inspect_simin_lotfi(conn):
    query="""
    SELECT *
    FROM time_entries T JOIN employees E on T.employee_id=E.employee_id
    WHERE E.name='Simin Lotfi'
    """
    df=pd.read_sql_query(query,conn)
    print("\n=== Simin Lotfi ===")
    print(df)

def query_financial_data(conn):
    query="""
    SELECT 
    f.project_no,
    p.project_name,
    f.construction_budget,
    f.date_updated
    FROM financial_data f
    LEFT JOIN projects p ON f.project_no=p.project_no
    ORDER BY f.construction_budget DESC
    LIMIT 10
    """
    df=pd.read_sql_query(query,conn)
    print("\n=== Financial Data ===")
    print(df)

def query_weekend_entries(conn):
    query="""
    SELECT employee_id,date,SUM(hours_worked) as total_hours
    FROM time_entries
    WHERE strftime('%w',date) IN ('0','6') -- 0=sunday,6=saturday
    GROUP BY employee_id,date
    """
    df=pd.read_sql_query(query,conn)
    print("\n=== Weekend Entries ===")
    print(df)




def query_project_costs(conn):
    query = """
    SELECT T.project_no,
           P.project_name,
           SUM(T.hours_worked * E.billable_rate) AS total_project_cost
    FROM time_entries T
    JOIN employees E ON T.employee_id = E.employee_id
    JOIN projects P ON T.project_no = P.project_no
    GROUP BY T.project_no, P.project_name
    ORDER BY total_project_cost DESC
    """
    df = pd.read_sql_query(query, conn)
    print("\n=== Project Costs (Total Amount by Project) ===")
    print(df)


def main():
    db_path="timekeeping.db" # database path
    conn=sqlite3.connect(db_path)
    query_top_projects(conn)
    query_top_employees(conn)
    query_hours_by_employee_and_month(conn)
    query_billable_vs_nonbillable_by_employee(conn)
    query_top_projects_by_month(conn)
    query_avg_daily_hours_by_employee(conn)
    query_highest_daily_hours(conn)
    query_company_monthly_trend(conn)
    query_financial_data(conn)
    query_weekend_entries(conn)
    query_project_costs(conn)
    query="""
    SELECT employee_id,billable_rate,position FROM employees
    """
    df=pd.read_sql_query(query,conn)
    print("\n=== Employees Billable Rate ===")
    print(df)
    conn.close()

if __name__=="__main__":
    main()
