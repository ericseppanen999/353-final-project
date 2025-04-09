import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import streamlit as st
import numpy as np

from utils.header_navigation import show_buttons#CUSTOM HEADER (utils folder)

show_buttons("Monthly Stats", "Insights into Monthly Business Trends & Productivity")

conn =sqlite3.connect('../timekeeping.db')

#extract from db tables
df_employees = pd.read_sql("SELECT employee_id, name FROM Employees", conn)
df_time = pd.read_sql("SELECT employee_id, date, hours_worked, work_code FROM time_entries", conn)
df_non_billable = pd.read_sql("SELECT employee_id, category, date, hours_worked FROM non_billable_entries", conn)

#transf
df_time["date"] = pd.to_datetime(df_time["date"])
df_time["month"] = df_time["date"].dt.to_period("M")
df_non_billable["date"] =pd.to_datetime(df_non_billable["date"])
df_non_billable["month"] = df_non_billable["date"].dt.to_period("M")
df = df_time.merge(df_employees, on="employee_id", how="left")

#SIDEBAR 
st.sidebar.header("Filter Data")

#months - This filters all the following vizs by month
df["year"]=df["month"].dt.year
df["month_num"]=df["month"].dt.month

years=sorted(df["year"].unique())
selected_year=st.sidebar.selectbox("Select a Year", years, index=len(years) - 1)

available_months=df[df["year"] == selected_year]["month_num"].unique()
available_months=sorted(available_months)
month_names={1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 
               6: "June", 7: "July", 8: "August", 9: "September", 
               10: "October", 11: "November", 12: "December"}

selected_month_num=st.sidebar.selectbox("Select a Month",available_months,format_func=lambda x: month_names[x])
selected_month_int=int(selected_month_num)
if selected_month_int>1:
    prev_year=selected_year
    prev_month_int=selected_month_int-1
else:
    prev_year=selected_year-1
    prev_month_int=12

prev_month=f"{prev_year}-{prev_month_int:02d}"
print("prev_month", prev_month)
print("prev_year", prev_year)
# Construct period string
selected_month = f"{selected_year}-{selected_month_num:02d}"

def calc_pct_increase(row):
    pct=0.0
    if row["prev_hours"] == 0:
        pct=0.0
    else:
        pct = ((row["hours_worked"] - row["prev_hours"]) / row["prev_hours"]) * 100
    if pct==0:
        return "0.00%"
    if pct>0:
        return f"+{pct:.2f}%"
    else:
        return f"-{pct:.2f}%"


filtered_df = df[df["month"].astype(str) ==selected_month]#filter by month
filtered_non_billable_df = df_non_billable[df_non_billable["month"].astype(str) == selected_month]#filter non-billable data based on month


#hours vars
employee_hours = filtered_df.groupby(["employee_id", "name"])["hours_worked"].sum().reset_index()
employee_hours["prev_hours"]=employee_hours["hours_worked"].shift(1)
employee_hours["prev_hours"]=employee_hours["prev_hours"].fillna(0)
employee_hours["pct_change"]=employee_hours.apply(calc_pct_increase,axis=1)
employee_hours["prev_hours"]=employee_hours["prev_hours"].fillna(0)
work_type_hours = filtered_df.groupby("work_code")["hours_worked"].sum().reset_index()
billable_hours = filtered_df["hours_worked"].sum()
non_billable_hours = filtered_non_billable_df["hours_worked"].sum()


billable_vs_non_billable_df = pd.DataFrame({
    "category": ["Billable", "Non-Billable"],
    "hours_worked": [billable_hours, non_billable_hours]
})


employee_hours = employee_hours.sort_values(by="hours_worked",ascending=False)

fig1 = px.bar(employee_hours, x="name", y="hours_worked",
              labels={"hours_worked": "Hours Worked", "name": "Employee"},
              color="hours_worked", color_continuous_scale="Blues",
              width=700, height=500)  # Increased figure size

fig1.update_traces(text=employee_hours["pct_change"], textposition="outside")
fig1.update_layout(
    margin=dict(t=60, b=60),
    uniformtext_minsize=8,
    uniformtext_mode='hide',
    title_text=f"Total Billable Hours per Employee ({selected_month})<br><sup>with % Increase vs {prev_month}</sup>",
    title_x=0.5
)

fig2 = px.pie(work_type_hours, names="work_code", values="hours_worked",
              labels={"work_code": "Work Type", "hours_worked": "Total Hours"},
              color_discrete_sequence=px.colors.sequential.Blues,
              width=600, height=500)  # Increased figure size



#we need a more advanced query for fig 3
#setup for fig3
query = f"""
    SELECT te.project_no, SUM(te.hours_worked) AS total_hours
    FROM time_entries te
    WHERE te.date LIKE '{selected_month}%'  -- filter by selected month
    GROUP BY te.project_no
    ORDER BY total_hours DESC  -- Sort by total hours worked in descending order
    LIMIT 5;  -- get top5 projects (or fewer if there are less than 5)
"""
top_projects_df = pd.read_sql(query, conn)
top_projects_df = top_projects_df.merge(pd.read_sql("SELECT project_no, project_name FROM projects", conn), on="project_no", how="left")


fig3 = px.bar(top_projects_df, 
              x="project_name", 
              y="total_hours", 
              labels={"total_hours": "Total Hours Worked", "project_name": "Project"},
              color="total_hours", 
              color_continuous_scale="Blues", 
              width=600, height=500)

fig4 = px.pie(billable_vs_non_billable_df, 
              names="category", 
              values="hours_worked",
              labels={"category": "Category", "hours_worked": "Total Hours"},
              color="category", 
              color_discrete_sequence=["#1f77b4", "#a3c4f3"],#MANUAL CHANGE HEX 
              width=600, height=500)


col1, spacer, col2 = st.columns([3.5, 0.1, 2.5])#columns - adjust these nums for size/proportion
#the middle one is a spacer


#COLUMN SETUP
#left one
with col1:
    #top
    st.subheader(f"Total Billable Hours Worked per Employee ({selected_month})")
    st.plotly_chart(fig1, use_container_width=True)
    
    #bott
    st.subheader(f"Top 5 Projects by Total Hours Worked ({selected_month})")
    st.plotly_chart(fig3, use_container_width=True)

#right one
with col2:
    
    st.subheader(f"Work Type Breakdown ({selected_month})")
    st.plotly_chart(fig2, use_container_width=True)
    

    st.subheader(f"Billable vs Non-Billable Hours ({selected_month})")
    st.plotly_chart(fig4, use_container_width=True)



