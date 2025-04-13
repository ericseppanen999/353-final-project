import sqlite3
import pandas as pd

def month_to_season(month):
    if month in [12,1,2]:
        return "Winter"
    elif month in [3,4,5]:
        return "Spring"
    elif month in [6,7,8]:
        return "Summer"
    else:
        return "Fall"

def load_monthly_hours(db_path="../timekeeping.db"):
    conn=sqlite3.connect(db_path)
    emp=pd.read_sql("""SELECT employee_id,name,position FROM employees""",conn)
    # add is_senior column
    # change to just titles TODO
    emp['is_senior']=emp['position'].str.contains("Senior|Principal", na=False).astype(int)

    bill=pd.read_sql("SELECT employee_id, date, hours_worked FROM time_entries", conn)
    nonb=pd.read_sql("SELECT employee_id, date, hours_worked FROM non_billable_entries",conn)
    conn.close()

    df=pd.concat([bill,nonb],ignore_index=True)
    df['month_dt']=pd.to_datetime(df['date']).dt.to_period('M').dt.to_timestamp()
    # group by monthly
    monthly=(df.groupby(['employee_id', 'month_dt'])['hours_worked'].sum().reset_index().rename(columns={'hours_worked':'total_hours'}))
    # join with employee data
    monthly=monthly.merge(emp,on='employee_id',how='left')
    return monthly

def load_seasonal_hours(db_path="../timekeeping.db"):
    #load monthly hours from db
    monthly=load_monthly_hours(db_path)

    # convert month to season and seniority
    monthly['season']=monthly['month_dt'].dt.month.apply(month_to_season)
    monthly['seniority']=monthly['is_senior'].map({0:'Junior',1:'Senior'})
    
    # group by season and seniority
    seasonal=(monthly.groupby(['seniority','season'])['total_hours'].agg(median='median',count='count').reset_index())
    # seasons in cal order
    season_order=["Winter","Spring","Summer","Fall"]
    seasonal['season']=pd.Categorical(seasonal['season'],categories=season_order,ordered=True)
    seasonal=seasonal.sort_values(['seniority','season'])
    return seasonal
