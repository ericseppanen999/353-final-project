import sqlite3
import pandas as pd

def load_phase_data(db_path="../timekeeping.db", phase_map=None):
    """
    Load time_entries joined with employees & projects,
    map each work_code to a 'phase', and compute cost=hours*rate.
    """
    if phase_map is None:
        phase_map = {}
    
    conn = sqlite3.connect(db_path)
    query = """
    SELECT 
        T.project_no,
        T.work_code,
        T.hours_worked,
        T.date,
        E.billable_rate,
        P.project_name
    FROM time_entries T
    JOIN employees E ON T.employee_id = E.employee_id
    JOIN projects P ON T.project_no = P.project_no
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    def get_phase(code):
        #return code
        return phase_map.get(code, "Other")
    df['phase'] = df['work_code'].apply(get_phase)
    df['cost'] = df['hours_worked'] * df['billable_rate']
    return df

def summarize_time_and_cost_by_phase(df):
    grouped = df.groupby(['project_no','project_name','phase']).agg(
        total_hours=('hours_worked','sum'),
        total_cost=('cost','sum')
    ).reset_index()
    grouped = grouped.sort_values('total_cost', ascending=False)
    return grouped

