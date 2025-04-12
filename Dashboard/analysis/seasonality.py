import sqlite3
import pandas as pd

def month_to_season(month: int) -> str:
    """Map month number to season name."""
    if month in [12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Spring"
    elif month in [6, 7, 8]:
        return "Summer"
    else:
        return "Fall"

def load_monthly_hours(db_path="../timekeeping.db") -> pd.DataFrame:
    """
    Returns a DataFrame with:
      - employee_id
      - month_dt (Timestamp)
      - total_hours (sum of billable + non‑billable)
      - name, position, is_senior
    """
    conn = sqlite3.connect(db_path)
    # Employee info
    emp = pd.read_sql("""
        SELECT employee_id, name, position
        FROM employees
    """, conn)
    emp['is_senior'] = emp['position'].str.contains("Senior|Principal", na=False).astype(int)

    # Billable and non‑billable entries
    bill = pd.read_sql("SELECT employee_id, date, hours_worked FROM time_entries", conn)
    nonb = pd.read_sql("SELECT employee_id, date, hours_worked FROM non_billable_entries", conn)
    conn.close()

    # Combine and aggregate by month
    df = pd.concat([bill, nonb], ignore_index=True)
    df['month_dt'] = pd.to_datetime(df['date']).dt.to_period('M').dt.to_timestamp()
    monthly = (
        df.groupby(['employee_id', 'month_dt'])['hours_worked']
          .sum()
          .reset_index()
          .rename(columns={'hours_worked':'total_hours'})
    )

    # Join back employee info
    monthly = monthly.merge(emp, on='employee_id', how='left')
    return monthly

def load_seasonal_hours(db_path="../timekeeping.db") -> pd.DataFrame:
    """
    Returns a summary DataFrame with columns:
      - is_senior (Senior/Junior)
      - season (Winter/Spring/Summer/Fall)
      - median (median total_hours)
      - count (number of observations)
    """
    # 1) Load monthly hours with senior flag
    monthly = load_monthly_hours(db_path)

    # 2) Assign seasons
    monthly['season'] = monthly['month_dt'].dt.month.apply(month_to_season)

    # 3) Map senior flag to labels
    monthly['seniority'] = monthly['is_senior'].map({0:'Junior', 1:'Senior'})

    # 4) Aggregate median & count by seniority and season
    seasonal = (
        monthly
          .groupby(['seniority','season'])['total_hours']
          .agg(median='median', count='count')
          .reset_index()
    )
    # Ensure seasons are in calendar order
    season_order = ["Winter","Spring","Summer","Fall"]
    seasonal['season'] = pd.Categorical(seasonal['season'], categories=season_order, ordered=True)
    seasonal = seasonal.sort_values(['seniority','season'])
    return seasonal
