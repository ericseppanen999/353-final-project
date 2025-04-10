import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

from sample_analysis.forecasting import forecast_expenditure,clean_project_no
from utils.header_navigation import show_buttons

st.title("Project Insights")
conn=sqlite3.connect('../timekeeping.db') # connect to db
projects_df=pd.read_sql("SELECT project_no, project_name FROM projects ORDER BY project_no",conn) # fetch projects

if projects_df.empty:
    st.error("No projects available.") # no projects
else:
    projects_df["display"]=projects_df["project_no"].astype(str)+" - "+projects_df["project_name"] # create display column
    search_query=st.sidebar.text_input("Search Projects","") # search input
    
    filtered_projects=projects_df[projects_df["display"].str.contains(search_query,case=False,na=False)] if search_query else projects_df # filter projects

    if filtered_projects.empty:
        st.sidebar.warning("No projects match your search.") # no matches
    else:
        default_project_no="1901" # default project
        default_display=filtered_projects[filtered_projects["project_no"].astype(str)==default_project_no]["display"].iloc[0] if default_project_no in filtered_projects["project_no"].astype(str).values else None

        selected_proj=st.sidebar.selectbox("Select a Project",filtered_projects["display"].tolist(),
                                           index=filtered_projects["display"].tolist().index(default_display) if default_display else 0) # project dropdown

        selected_proj_no=selected_proj.split(" - ")[0].strip() # extract project no
        st.write(f"### Work History for Project {selected_proj_no}")


        #KPI Section 
        project_info_query = f"""
        SELECT p.project_captain, f.percent_complete, f.amount_left_to_bill
        FROM projects p
        LEFT JOIN financial_data f ON p.project_no = f.project_no
        WHERE p.project_no = '{selected_proj_no}'
        """
        
        kpi_df =pd.read_sql(project_info_query, conn)
        
        if not kpi_df.empty :
            
            captain = kpi_df["project_captain"].iloc[0]
            percent_complete_raw = kpi_df["percent_complete"].iloc[0]
            amount_left = kpi_df["amount_left_to_bill"].iloc[0]
        
            #percent complete (converts frac to percent)
            if pd.isnull(percent_complete_raw) or percent_complete_raw <= 0:
                
                percent_complete_display = "N/A"
            elif percent_complete_raw >= 1.0:
                percent_complete_display = "100%"
                
            else :
                percent_complete_display = f"{percent_complete_raw * 100:.1f}%"
        
            #hours
            hours_query = f"""
            SELECT hours_worked
            FROM time_entries
            WHERE project_no = '{selected_proj_no}'
            """
            
            hours_df =pd.read_sql(hours_query,conn)
            total_hours = hours_df["hours_worked"].sum()

            #the kpis are split into 4 columns so they go across the screen
            col1, col2, col3, col4 =st.columns(4)
            
            col1.metric("📋 Job Captain", captain if captain else "N/A")
            col2.metric("✅ Completion %", percent_complete_display)
            col3.metric("💸 Left to Bill", f"${amount_left:,.2f}" if pd.notnull(amount_left) and percent_complete_raw < 1.0 else "✓ Fully Billed")
            col4.metric("⏱️ Total Hours Logged", f"{total_hours:,.1f}")
        else:
            
            st.warning("No KPI data available for this project.")

            



    

        query=f"SELECT date, hours_worked FROM time_entries WHERE project_no = '{selected_proj_no}'" # fetch time entries
        df_time=pd.read_sql(query,conn)

        if df_time.empty:
            st.warning("No time entries found for this project.") # no time entries
        else:
            df_time["date"]=pd.to_datetime(df_time["date"]) # convert to datetime
            df_time["month"]=df_time["date"].dt.to_period("M").astype(str) # extract month
            df_time["day_of_week"]=df_time["date"].dt.dayofweek # extract day of week
            def categorize(row): # categorize work type
                if row["day_of_week"]>=5:
                    return "Weekend"
                elif row["hours_worked"]>7.5:
                    return "Overtime"
                else:
                    return "Regular"
            df_time["type"]=df_time.apply(categorize,axis=1) # apply categorization
            agg_df=df_time.groupby(["month","type"])["hours_worked"].sum().reset_index() # aggregate data
            fig=px.bar(agg_df,
                       x="month",y="hours_worked",
                       color="type",
                       title=f"Work Hours Breakdown per Month for Project {selected_proj_no}",
                       labels={"month":"Month","hours_worked":"Hours Worked","type":"Work Type"},
                       category_orders={"type":["Regular","Overtime","Weekend"]}) # create bar chart
            st.plotly_chart(fig,use_container_width=True)
            st.markdown("---")
            st.subheader("📈 Expenditure Forecast")

            with st.expander("Generate Forecast Report"):
                forecast_months=st.slider("Months to Forecast",min_value=1,max_value=12,value=3) # forecast slider
                if st.button("Run Forecast"): # forecast button
                    forecast_df=forecast_expenditure(selected_proj_no,forecast_months,db_path="../timekeeping.db",rate=100.0) # run forecast

                    if forecast_df is not None:
                        # get historical data
                        def get_monthly_expenditure(project_no,db_path="timekeeping.db",rate=100.0): # fetch expenditure
                            conn=sqlite3.connect(db_path)
                            query=f"""
                              SELECT strftime('%Y-%m', date) AS month, SUM(hours_worked) AS total_hours
                              FROM time_entries
                              WHERE project_no = '{project_no}'
                              GROUP BY month
                              ORDER BY month;
                            """
                            df=pd.read_sql_query(query,conn)
                            conn.close()
                            if df.empty:
                                return pd.DataFrame()
                            df['expenditure']=df['total_hours']*rate # calculate expenditure
                            df['ds']=pd.to_datetime(df['month']+"-01") # convert to datetime
                            return df[['ds','expenditure']]

                        historical_df=get_monthly_expenditure(selected_proj_no,db_path="../timekeeping.db",rate=100.0) # get historical data
                        historical_df=historical_df.rename(columns={'expenditure':'Actual Expenditure'}) # rename column
                        forecast_df=forecast_df.rename(columns={'forecast_expenditure':'Forecasted Expenditure'}) # rename column

                        combined_df=pd.concat([
                            historical_df.set_index('ds'),
                            forecast_df.set_index('ds')
                        ],axis=1).reset_index().rename(columns={'index':'Date'}) # combine data

                        fig2=px.line(combined_df,
                                     x='ds',
                                     y=['Actual Expenditure','Forecasted Expenditure'],
                                     title=f"Forecasted Expenditure for Project {selected_proj_no}",
                                     labels={"value":"Expenditure ($)","variable":"Legend"},
                                     markers=True) # create line chart

                        st.plotly_chart(fig2,use_container_width=True)
                    else:
                        st.warning("Not enough data to generate a forecast.") # insufficient data

conn.close()
