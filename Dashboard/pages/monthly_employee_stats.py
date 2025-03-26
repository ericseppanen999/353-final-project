import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import streamlit as st



conn=sqlite3.connect('../timekeeping.db')

st.title("Monthly Employee Stats")
st.write("Insights into Monthly Productivity Trends & Performance")


df_employees = pd.read_sql("SELECT employee_id, name FROM Employees", conn)
df_time = pd.read_sql("SELECT employee_id, date, hours_worked FROM time_entries", conn)


df_time["date"] =pd.to_datetime(df_time["date"])
df_time["month"] = df_time["date"].dt.to_period("M")  # Extract Month-Year


df = df_time.merge(df_employees, on="employee_id", how="left")

#sidebar filter
st.sidebar.header("Filter Data")



#months
months = df["month"].astype(str).unique()
selected_month = st.sidebar.selectbox("Select a Month", months, index=len(months) - 1)  # Default to latest


filtered_df =df[df["month"].astype(str) == selected_month]#filter based on month

#aggregate work hours by employee
employee_hours = filtered_df.groupby(["employee_id", "name"])["hours_worked"].sum().reset_index()

#bar chart
st.subheader(f"Total Hours Worked per Employee ({selected_month})")
fig1 = px.bar(employee_hours, x="name", y="hours_worked", title=f"Total Work Hours per Employee ({selected_month})",
              labels={"hours_worked": "Hours Worked", "name": "Employee"},
              color="hours_worked", color_continuous_scale="Blues")
st.plotly_chart(fig1)

