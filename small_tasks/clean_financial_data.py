import sqlite3
import pandas as pd
import numpy as np

def parse_dollar_range(value):
    if pd.isnull(value):
        return np.nan
    val_str=str(value).strip().replace("$","")
    if "-" in val_str:
        parts=val_str.split("-")
        try:
            nums=[float(x.strip()) for x in parts]
            return sum(nums)/len(nums)
        except ValueError:
            return np.nan
    else:
        try:
            return float(val_str)
        except ValueError:
            return np.nan

if __name__=="__main__":
    db_path="timekeeping.db"
    conn=sqlite3.connect(db_path)
    df=pd.read_sql("SELECT * FROM financial_data",conn)

    if "target_fees_per_hour" in df.columns:
        df["target_fees_per_hour"]=df["target_fees_per_hour"].apply(parse_dollar_range)

    if "actual_fees_per_hour" in df.columns:
        df["actual_fees_per_hour"]=df["actual_fees_per_hour"].apply(parse_dollar_range)

    df.to_sql("financial_data",conn,if_exists="replace",index=False)
    conn.close()
