import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
from analysis.forecasting import forecast_expenditure,clean_project_no # forecasting imports
from utils.header_navigation import show_buttons
from analysis.time_cost_phase import load_phase_data,summarize_time_and_cost_by_phase # phase analysis imports
from analysis.cluster import run_dbscan_workflow
from sklearn.decomposition import PCA

st.title("Project Insights")
conn=sqlite3.connect('../timekeeping.db') # connect to db

projects_df=pd.read_sql("SELECT project_no,project_name FROM projects ORDER BY project_no",conn) # fetch projects

if projects_df.empty:st.error("No projects available.")

st.subheader("DBSCAN Clustering (All Projects)")

eps_val=st.slider("eps (Neighborhood Radius)",0.1,3.0,0.5,0.1) # slider for eps
min_samps_val=st.slider("min_samples (Density Threshold)",1,20,5) # slider for min_samples

if st.button("Run DBSCAN"): # run dbscan
    df_result,data_scaled,labels=run_dbscan_workflow(db_path="../timekeeping.db",eps=eps_val,min_samples=min_samps_val)

    n_clusters=len(set(labels)-{-1}) # calculate clusters
    n_outliers=sum(labels==-1) # calculate outliers
    st.write(f"**Number of Clusters (excluding noise)**: {n_clusters}")
    st.write(f"**Number of Outliers (noise points)**: {n_outliers}")

    pca=PCA(n_components=2,random_state=42) # pca for plotting
    pca_coords=pca.fit_transform(data_scaled)
    
    df_plot=pd.DataFrame({'PC1':pca_coords[:,0],'PC2':pca_coords[:,1],'cluster_label':labels})

    fig_dbscan=px.scatter(df_plot,x='PC1',y='PC2',color='cluster_label',title='DBSCAN Clusters (2D PCA Projection)',labels={'PC1':'Principal Component 1','PC2':'Principal Component 2'})
    st.plotly_chart(fig_dbscan,use_container_width=True)

    st.subheader("All Projects with Cluster Labels") # show cluster labels
    st.dataframe(df_result[['project_no','cluster_label']])

projects_df["display"]=projects_df["project_no"].astype(str)+" - "+projects_df["project_name"] # create display column
search_query=st.sidebar.text_input("Search Projects","") # search input

filtered_projects=(projects_df[projects_df["display"].str.contains(search_query,case=False,na=False)]if search_query else projects_df) # filter projects

if filtered_projects.empty:st.sidebar.warning("No projects match your search.")
else:
    default_project_no="1901" # default project
    if default_project_no in filtered_projects["project_no"].astype(str).values:
        default_display=filtered_projects[filtered_projects["project_no"].astype(str)==default_project_no]["display"].iloc[0]
    else:default_display=None

    selected_proj=st.sidebar.selectbox("Select a Project",filtered_projects["display"].tolist(),index=filtered_projects["display"].tolist().index(default_display)if default_display else 0) # select project
    selected_proj_no=selected_proj.split(" - ")[0].strip()
    st.write(f"### Work History for Project {selected_proj_no}")

    project_info_query=f"""
    SELECT p.project_captain,f.percent_complete,f.amount_left_to_bill
    FROM projects p
    LEFT JOIN financial_data f ON p.project_no=f.project_no
    WHERE p.project_no='{selected_proj_no}'
    """
    kpi_df=pd.read_sql(project_info_query,conn) # fetch kpi data

    if not kpi_df.empty:
        captain=kpi_df["project_captain"].iloc[0]
        percent_complete_raw=kpi_df["percent_complete"].iloc[0]
        amount_left=kpi_df["amount_left_to_bill"].iloc[0]

        if pd.isnull(percent_complete_raw)or percent_complete_raw<=0:percent_complete_display="N/A" # handle percent complete
        elif percent_complete_raw>=1.0:percent_complete_display="100%"
        else:percent_complete_display=f"{percent_complete_raw*100:.1f}%"

        hours_query=f"""
        SELECT hours_worked
        FROM time_entries
        WHERE project_no='{selected_proj_no}'
        """
        hours_df=pd.read_sql(hours_query,conn) # fetch hours
        total_hours=hours_df["hours_worked"].sum()

        col1,col2,col3,col4=st.columns(4) # display metrics
        col1.metric("Job Captain",captain if captain else "N/A")
        col2.metric("Completion %",percent_complete_display)
        col3.metric("Left to Bill",f"${amount_left:,.2f}"if pd.notnull(amount_left)and percent_complete_raw<1.0 else "✓ Fully Billed")
        col4.metric("Total Hours Logged",f"{total_hours:,.1f}")
    else:st.warning("No KPI data available for this project.")

    query=f"SELECT date,hours_worked FROM time_entries WHERE project_no='{selected_proj_no}'"
    df_time=pd.read_sql(query,conn) # fetch time entries

    if df_time.empty:st.warning("No time entries found for this project.")
    else:
        df_time["date"]=pd.to_datetime(df_time["date"])
        df_time["month"]=df_time["date"].dt.to_period("M").astype(str)
        df_time["day_of_week"]=df_time["date"].dt.dayofweek

        def categorize(row): # categorize work type
            if row["day_of_week"]>=5:return "Weekend"
            elif row["hours_worked"]>7.5:return "Overtime"
            else:return "Regular"

        df_time["type"]=df_time.apply(categorize,axis=1)
        agg_df=df_time.groupby(["month","type"])["hours_worked"].sum().reset_index()

        fig=px.bar(agg_df,x="month",y="hours_worked",color="type",title=f"Work Hours Breakdown per Month for Project {selected_proj_no}",labels={"month":"Month","hours_worked":"Hours Worked","type":"Work Type"},category_orders={"type":["Regular","Overtime","Weekend"]}) # bar chart
        st.plotly_chart(fig,use_container_width=True)

        st.markdown("---")
        st.subheader("📈 Expenditure Forecast")

        with st.expander("Generate Forecast Report"): # forecast report
            forecast_months=st.slider("Months to Forecast",min_value=1,max_value=3,value=3)
            if st.button("Run Forecast"):
                forecast_df=forecast_expenditure(selected_proj_no,forecast_months,db_path="../timekeeping.db")
                if forecast_df is not None:
                    def get_monthly_expenditure(project_no,db_path="timekeeping.db"): # fetch monthly expenditure
                        conn_inner=sqlite3.connect(db_path)
                        query=f"""
                            SELECT strftime('%Y-%m',T.date)AS month,
                                    SUM(T.hours_worked*CAST(E.billable_rate AS INTEGER))AS total_expenditure
                            FROM time_entries T
                            JOIN employees E ON T.employee_id=E.employee_id
                            WHERE T.project_no='{project_no}'
                            GROUP BY month
                            ORDER BY month;
                        """
                        df_hist=pd.read_sql_query(query,conn_inner)
                        conn_inner.close()
                        if df_hist.empty:return pd.DataFrame()
                        df_hist["expenditure"]=df_hist["total_expenditure"]
                        df_hist["ds"]=pd.to_datetime(df_hist["month"]+"-01")
                        return df_hist[["ds","expenditure"]]

                    historical_df=get_monthly_expenditure(selected_proj_no,db_path="../timekeeping.db")
                    historical_df=historical_df.rename(columns={'expenditure':'Actual Expenditure'})
                    forecast_df=forecast_df.rename(columns={'forecast_expenditure':'Forecasted Expenditure'})

                    combined_df=pd.concat([historical_df.set_index("ds"),forecast_df.set_index("ds")],axis=1).reset_index().rename(columns={'index':'Date'})

                    fig2=px.line(combined_df,x="ds",y=["Actual Expenditure","Forecasted Expenditure"],title=f"Forecasted Expenditure for Project {selected_proj_no}",labels={"value":"Expenditure ($)","variable":"Legend"},markers=True) # line chart
                    st.plotly_chart(fig2,use_container_width=True)
                else:st.warning("Not enough data to generate a forecast.")
    st.markdown("---")
    st.subheader("Phase Analysis for This Project")
    with st.expander("View Time & Cost by Phase"): # phase analysis
        phase_map={"BP":"Building Permit Drawings","DP":"Development Permit Drawings","CD":"Construction Documents","CA":"Construction Administration","D":"Design Phase","TEND":"Tendering","ADM":"Admin","DP 1a":"Development Permit Drawings 1a","DP 1b":"Development Permit Drawings 1b","DP 1c":"Development Permit Drawings 1c","DP 2a":"Development Permit Drawings 2a","DP 2b":"Development Permit Drawings 2b","DP 2c":"Development Permit Drawings 2c","BP 1a":"Building Permit Drawings 1a","BP 1b":"Building Permit Drawings 1b","BP 1c":"Building Permit Drawings 1c","BP 2a":"Building Permit Drawings 2a","BP 2b":"Building Permit Drawings 2b","BP 2c":"Building Permit Drawings 2c","BP 3a":"Building Permit Drawings 3a","BP 3b":"Building Permit Drawings 3b","BP 3c":"Building Permit Drawings 3c","nan":"Empty Work Code"}

        df_phases=load_phase_data(db_path="../timekeeping.db",phase_map=phase_map) # load phase data
        df_phases_selected=df_phases[df_phases["project_no"]==selected_proj_no]
        
        if df_phases_selected.empty:st.warning("No phase data found for this project.")
        else:
            phase_summary=summarize_time_and_cost_by_phase(df_phases_selected) # summarize phase data

            fig_phase=px.bar(phase_summary,x='phase',y='total_cost',hover_data=['total_hours','total_cost'],title=f"Time & Cost by Phase for Project {selected_proj_no}",labels={'phase':'Project Phase','total_cost':'Total Cost ($)'},color='total_cost',color_continuous_scale=px.colors.sequential.Viridis) # bar chart
            fig_phase.update_traces(texttemplate='%{y:.2f}',textposition='outside')
            fig_phase.update_layout(uniformtext_minsize=8,uniformtext_mode='hide')
            st.plotly_chart(fig_phase,use_container_width=True)

            fig_pie=px.pie(phase_summary,names='phase',values='total_cost',title=f"Cost Distribution by Phase for Project {selected_proj_no}",color='phase',color_discrete_sequence=px.colors.qualitative.Plotly) # pie chart
            st.plotly_chart(fig_pie,use_container_width=True)

            st.dataframe(phase_summary) # display table
        st.subheader("Aggregated Phase Data Across ALL Projects")

        filtered_df_phases=df_phases[df_phases['phase']!="Empty Work Code"] # filter empty work codes

        all_phase_summary=(filtered_df_phases.groupby('phase').agg(total_hours=('hours_worked','sum'),total_cost=('cost','sum')).reset_index()) # aggregate phase data

        st.write("### Aggregated Phase Summary") # display aggregated summary

        fig_all=px.pie(all_phase_summary,names='phase',values='total_cost',title="Overall Cost Distribution by Phase (All Projects)",color='phase',color_discrete_sequence=px.colors.qualitative.Plotly) # pie chart for all projects
        st.plotly_chart(fig_all,use_container_width=True)
conn.close()
