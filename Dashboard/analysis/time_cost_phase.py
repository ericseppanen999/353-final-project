import sqlite3
import pandas as pd

def load_phase_data(db_path="../timekeeping.db",phase_map=None):
    if phase_map is None:
        phase_map={}
    conn=sqlite3.connect(db_path)
    query="""SELECT T.project_no,T.work_code,T.hours_worked,T.date,E.billable_rate,P.project_name
    FROM time_entries T JOIN employees E ON T.employee_id=E.employee_id JOIN projects P ON T.project_no=P.project_no"""
    df=pd.read_sql_query(query,conn)
    conn.close()

    df['date']=pd.to_datetime(df['date'],errors='coerce')
    
    def get_phase(code):
        #return code
        return phase_map.get(code, "Other")
    df['phase'] = df['work_code'].apply(get_phase)
    df['cost'] = df['hours_worked'] * df['billable_rate']
    #print(df.head())
    return df

def find_time_entries(project_no,db_path="../timekeeping.db"):
    query=f"SELECT date,hours_worked FROM time_entries WHERE project_no='{project_no}'"
    conn=sqlite3.connect(db_path)
    df=pd.read_sql(query,conn)
    #print("len(df)")
    if df.empty:
        return "No data found for project {project_no}"
    else:
        # adjust time entries for analysis
        df["date"]=pd.to_datetime(df["date"])
        df["month"]=df["date"].dt.to_period("M").astype(str)
        df["day_of_week"]=df["date"].dt.dayofweek
        #print(df['day_of_week'].unique().count())
        #print(df['day_of_week'].unique())
        def categorize(row):
            if row["day_of_week"]>=5:
                return "Weekend"
            elif row["hours_worked"]>7.5:
                return "Overtime"
            else:
                return "Regular"
        # categorize work types
        df["type"]=df.apply(categorize,axis=1)
        #print(df_time.head())
        # group by month and type
        agg_df=df.groupby(["month","type"])["hours_worked"].sum().reset_index()
        agg_df["project_no"]=project_no
    return agg_df


def get_project_summary(project_no,db_path="../timekeeping.db"):
    conn=sqlite3.connect(db_path)
    query=f"""
    SELECT p.project_captain,f.percent_complete,f.amount_left_to_bill
    FROM projects p LEFT JOIN financial_data f ON p.project_no=f.project_no
    WHERE p.project_no='{project_no}'
    """
    df=pd.read_sql_query(query,conn)
    return df


def summarize_time_and_cost_by_phase(df):
    grouped=df.groupby(['project_no','project_name','phase']).agg(total_hours=('hours_worked','sum'),total_cost=('cost','sum')).reset_index()
    grouped=grouped.sort_values('total_cost',ascending=False)
    return grouped

