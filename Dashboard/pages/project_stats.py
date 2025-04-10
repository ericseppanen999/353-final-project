import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

from sample_analysis.forecasting import forecast_expenditure, clean_project_no
from utils.header_navigation import show_buttons

st.title("Project Work Over Time")

conn = sqlite3.connect('../timekeeping.db')  # connect to DB
projects_df = pd.read_sql("SELECT project_no, project_name FROM projects ORDER BY project_no", conn)

if projects_df.empty:
    st.error("No projects available.")  # no projects
else:
    projects_df["display"] = projects_df["project_no"].astype(str) + " - " + projects_df["project_name"]
    search_query = st.sidebar.text_input("Search Projects", "")  # search input

    filtered_projects = (projects_df[projects_df["display"].str.contains(search_query, case=False, na=False)]
                         if search_query else projects_df)

    if filtered_projects.empty:
        st.sidebar.warning("No projects match your search.")  # no matches
    else:
        default_project_no = "1901"  # default project
        if default_project_no in filtered_projects["project_no"].astype(str).values:
            default_display = filtered_projects[filtered_projects["project_no"].astype(str) == default_project_no]["display"].iloc[0]
        else:
            default_display = None

        selected_proj = st.sidebar.selectbox("Select a Project", filtered_projects["display"].tolist(),
                                               index=filtered_projects["display"].tolist().index(default_display)
                                               if default_display else 0)
        selected_proj_no = selected_proj.split(" - ")[0].strip()
        st.write(f"### Work History for Project {selected_proj_no}")

        # Fetch time entries for the selected project
        query = f"SELECT date, hours_worked FROM time_entries WHERE project_no = '{selected_proj_no}'"
        df_time = pd.read_sql(query, conn)

        if df_time.empty:
            st.warning("No time entries found for this project.")
        else:
            df_time["date"] = pd.to_datetime(df_time["date"])
            df_time["month"] = df_time["date"].dt.to_period("M").astype(str)
            df_time["day_of_week"] = df_time["date"].dt.dayofweek

            def categorize(row):
                if row["day_of_week"] >= 5:
                    return "Weekend"
                elif row["hours_worked"] > 7.5:
                    return "Overtime"
                else:
                    return "Regular"

            df_time["type"] = df_time.apply(categorize, axis=1)
            agg_df = df_time.groupby(["month", "type"])["hours_worked"].sum().reset_index()

            fig = px.bar(agg_df,
                         x="month", y="hours_worked",
                         color="type",
                         title=f"Work Hours Breakdown per Month for Project {selected_proj_no}",
                         labels={"month": "Month", "hours_worked": "Hours Worked", "type": "Work Type"},
                         category_orders={"type": ["Regular", "Overtime", "Weekend"]})
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            st.subheader("📈 Expenditure Forecast")

            with st.expander("Generate Forecast Report"):
                forecast_months = st.slider("Months to Forecast", min_value=1, max_value=12, value=3)
                if st.button("Run Forecast"):
                    # Use updated forecast_expenditure; note: no need to pass a constant rate now.
                    forecast_df = forecast_expenditure(selected_proj_no, forecast_months, db_path="../timekeeping.db")
                    
                    if forecast_df is not None:
                        # UPDATED get_monthly_expenditure function to fetch historical data based on employee billable rates.
                        def get_monthly_expenditure(project_no, db_path="timekeeping.db"):
                            conn_inner = sqlite3.connect(db_path)
                            query = f"""
                                SELECT strftime('%Y-%m', T.date) AS month,
                                       SUM(T.hours_worked * CAST(E.billable_rate AS INTEGER)) AS total_expenditure
                                FROM time_entries T
                                JOIN employees E ON T.employee_id = E.employee_id
                                WHERE T.project_no = '{project_no}'
                                GROUP BY month
                                ORDER BY month;
                            """
                            df_hist = pd.read_sql_query(query, conn_inner)
                            conn_inner.close()
                            if df_hist.empty:
                                return pd.DataFrame()
                            df_hist["expenditure"] = df_hist["total_expenditure"]
                            df_hist["ds"] = pd.to_datetime(df_hist["month"] + "-01")
                            return df_hist[["ds", "expenditure"]]

                        historical_df = get_monthly_expenditure(selected_proj_no, db_path="../timekeeping.db")
                        historical_df = historical_df.rename(columns={'expenditure': 'Actual Expenditure'})
                        forecast_df = forecast_df.rename(columns={'forecast_expenditure': 'Forecasted Expenditure'})

                        combined_df = pd.concat([
                            historical_df.set_index("ds"),
                            forecast_df.set_index("ds")
                        ], axis=1).reset_index().rename(columns={'index': 'Date'})

                        fig2 = px.line(combined_df,
                                       x="ds",
                                       y=["Actual Expenditure", "Forecasted Expenditure"],
                                       title=f"Forecasted Expenditure for Project {selected_proj_no}",
                                       labels={"value": "Expenditure ($)", "variable": "Legend"},
                                       markers=True)
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.warning("Not enough data to generate a forecast.")

conn.close()
