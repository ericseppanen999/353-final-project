import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import linregress

def get_top10_trends(db_path="../timekeeping.db",start_date="2010-01-01"):
    conn=sqlite3.connect(db_path)
    bill_entries=pd.read_sql("SELECT employee_id, date, hours_worked FROM time_entries", conn)
    nonbill_entries=pd.read_sql("SELECT employee_id, date, hours_worked FROM non_billable_entries", conn)
    names=pd.read_sql("SELECT employee_id, name FROM employees",conn)
    conn.close()

    total_bill=bill_entries.groupby('employee_id')['hours_worked'].sum().reset_index()
    top10=total_bill.nlargest(10,'hours_worked')['employee_id'].tolist()

    bill_entries=bill_entries[bill_entries.date>=start_date].copy()
    nonbill_entries=nonbill_entries[nonbill_entries.date>=start_date].copy()

    def build_monthly(eid):
        # seperate billable and non-billable entries
        b=bill_entries[bill_entries.employee_id==eid].copy()
        n=nonbill_entries[nonbill_entries.employee_id==eid].copy()

        # convert date to datetime and extract month
        b['month']=pd.to_datetime(b.date).dt.to_period('M')
        n['month']=pd.to_datetime(n.date).dt.to_period('M')

        # group by month and sum hours worked
        mb=b.groupby('month')['hours_worked'].sum()
        mn=n.groupby('month')['hours_worked'].sum()
        # convert to data frame, rename columns, and join
        m=mb.rename('billable').to_frame().join(mn.rename('nonbillable'),how='outer').fillna(0).reset_index()

        # metrics
        m['total']=m.billable+m.nonbillable
        m['billable_pct']=m.billable/m.total
        m['month_dt']=m.month.dt.to_timestamp()

        # built month index
        m['month_idx']=m['month'].astype('period[M]').astype('int64').astype(int) # threw so many errors, not sure if best practice
        #print(m['month_idx'].dtype)
        m['m_idx']=m['month_idx']-m['month_idx'].min()
        #print(m['m_idx'])
        # center around mean for better interpretation
        mean_idx=m['m_idx'].mean()
        x_centered=m['m_idx']-mean_idx
        
        # lin regress
        slope,intercept,r,p,se=linregress(x_centered,m['billable_pct'])
        return m,slope,intercept,p

    trends=[]
    monthly_data={}
    for eid in top10:
        # get monthly data for each employee
        #print(f"Processing employee {eid}")
        mdf,slope,intercept,p=build_monthly(eid)
        name=names.loc[names.employee_id==eid,'name'].iloc[0]
        trends.append({'employee_id':eid,'name':name,'slope':slope,'intercept':intercept,'p_value':p,'mean_idx':mdf['m_idx'].mean()})
        monthly_data[eid]=mdf

    trends_df=pd.DataFrame(trends)
    return trends_df,monthly_data
