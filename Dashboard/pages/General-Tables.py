import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

from utils.header_navigation import show_buttons#CUSTOM HEADER (utils folder)

show_buttons("Timekeeping Tables", "Table Data")

#connect
conn = sqlite3.connect('../timekeeping.db')

#helper function
# takes SQL queries and returnvas a pandas df
def load_data(query):
    return pd.read_sql(query, conn)



#sidebar
#should be under pages tab
#lets you choose which table to look at
st.sidebar.header("Select Data to View")
data_option = st.sidebar.selectbox("Choose a table", ["Employees", "Projects", "Time Entries", "Non-Billable Entries"])



#table display
if data_option == "Employees":
    employee_query = "SELECT * FROM employees"
    employees_df = load_data(employee_query)
    st.write("### Employee Data", employees_df)

elif data_option == "Projects":
    project_query = "SELECT * FROM projects"
    projects_df = load_data(project_query)
    st.write("### Project Data", projects_df)

elif data_option == "Time Entries":
    time_entries_query = "SELECT * FROM time_entries"
    time_entries_df = load_data(time_entries_query)
    st.write("### Time Entries Data", time_entries_df)
    
    st.subheader("Visualize Time Entries")
    fig, ax = plt.subplots()
    time_entries_df.groupby('employee_id')['hours_worked'].sum().plot(kind='bar', ax=ax)
    ax.set_xlabel('Employee ID')
    ax.set_ylabel('Total Hours Worked')
    st.pyplot(fig)

elif data_option == "Non-Billable Entries":
    non_billable_query = "SELECT * FROM non_billable_entries"
    non_billable_df = load_data(non_billable_query)
    st.write("### Non-Billable Entries Data", non_billable_df)
    
    st.subheader("Visualize Non-Billable Entries")
    fig, ax = plt.subplots()
    non_billable_df.groupby('employee_id')['hours'].sum().plot(kind='bar', ax=ax)
    ax.set_xlabel('Employee ID')
    ax.set_ylabel('Total Hours (Non-Billable)')
    st.pyplot(fig)


conn.close()

