#!/usr/bin/env python3

import sqlite3
import pandas as pd
import numpy as np

def parse_dollar_range(value):
    """
    Convert strings like '$70-$80' into the average (e.g. 75.0).
    Convert '$70' to 70.0.
    Return np.nan if parsing fails.
    """
    if pd.isnull(value):
        return np.nan
    # Remove optional '$' sign
    val_str = str(value).strip().replace("$", "")
    # Check if it's a range
    if "-" in val_str:
        parts = val_str.split("-")
        try:
            nums = [float(x.strip()) for x in parts]
            return sum(nums) / len(nums)
        except ValueError:
            return np.nan
    else:
        # It's a single value like "70" or "70.5"
        try:
            return float(val_str)
        except ValueError:
            return np.nan

if __name__ == "__main__":
    db_path = "timekeeping.db"  # Adjust if your DB is elsewhere

    print("Connecting to database and loading financial_data table...")
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM financial_data", conn)

    # Apply parsing function to the columns you need to fix
    # Adjust column names if your table uses different field names
    if "target_fees_per_hour" in df.columns:
        df["target_fees_per_hour"] = df["target_fees_per_hour"].apply(parse_dollar_range)

    if "actual_fees_per_hour" in df.columns:
        df["actual_fees_per_hour"] = df["actual_fees_per_hour"].apply(parse_dollar_range)

    # Overwrite the financial_data table with the cleaned data
    print("Overwriting the financial_data table with cleaned numeric values...")
    df.to_sql("financial_data", conn, if_exists="replace", index=False)
    conn.close()
    print("Done. The problem should be fixed now!")
