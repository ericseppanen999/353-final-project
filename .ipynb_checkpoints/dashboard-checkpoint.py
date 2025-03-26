import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

# Connect to the SQLite database
conn = sqlite3.connect('timekeeping.db')
cursor = conn.cursor()

# Helper function to execute SQL queries and return results as a pandas DataFrame
def load_data(query):
    return pd.read_sql(query, conn)

# Streamlit UI
st.title("Timekeeping Dashboard")

# Option to view different tables
st.sidebar.header("Select Data to View")
data_option = st.sidebar.selectbox("Choose a table", ["Employees", "Projects", "Time Entries", "Non-Billable Entries"])

if data_option == "Employees":
    # Load and display employee data
    employee_query = "SELECT * FROM employees"
    employees_df = load_data(employee_query)
    st.write("### Employee Data", employees_df)

elif data_option == "Projects":
    # Load and display project data
    project_query = "SELECT * FROM projects"
    projects_df = load_data(project_query)
    st.write("### Project Data", projects_df)

elif data_option == "Time Entries":
    # Load and display time entries data
    time_entries_query = "SELECT * FROM time_entries"
    time_entries_df = load_data(time_entries_query)
    st.write("### Time Entries Data", time_entries_df)
    
    # Visualize time entries
    st.subheader("Visualize Time Entries")
    fig, ax = plt.subplots()
    time_entries_df.groupby('employee_id')['hours_worked'].sum().plot(kind='bar', ax=ax)
    ax.set_xlabel('Employee ID')
    ax.set_ylabel('Total Hours Worked')
    st.pyplot(fig)

elif data_option == "Non-Billable Entries":
    # Load and display non-billable entries data
    non_billable_query = "SELECT * FROM non_billable_entries"
    non_billable_df = load_data(non_billable_query)
    st.write("### Non-Billable Entries Data", non_billable_df)
    
    # Visualize non-billable entries
    st.subheader("Visualize Non-Billable Entries")
    fig, ax = plt.subplots()
    non_billable_df.groupby('employee_id')['hours'].sum().plot(kind='bar', ax=ax)
    ax.set_xlabel('Employee ID')
    ax.set_ylabel('Total Hours (Non-Billable)')
    st.pyplot(fig)

# Close the database connection when done
conn.close()