import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
from analysis.forecasting import forecast_expenditure,get_monthly_expenditure
from utils.header_navigation import show_buttons
from analysis.time_cost_phase import load_phase_data,summarize_time_and_cost_by_phase,find_time_entries,get_project_summary
from analysis.cluster import run_kmeans
from sklearn.decomposition import PCA

from utils.header_navigation import show_buttons#CUSTOM HEADER (utils folder)

show_buttons("Project Insights", "Insights into Project Performance & Clustering")

st.title("Project Insights")
conn=sqlite3.connect('../timekeeping.db') # connect to db

projects_df=pd.read_sql("SELECT project_no,project_name FROM projects ORDER BY project_no",conn) # fetch projects

if projects_df.empty:
    st.error("No projects available.")
st.subheader("K-Means Clustering")
st.write("This section allows you to run a clustering algorithm on the project data to identify patterns and group similar projects together.")
st.write("The axes are labeled as PC1 and PC2, in short, PCA is used to reduce dimensionality of data to capture the most important features.")
k=st.slider("Number of Clusters", min_value=1, max_value=10, value=3)
if st.button("Run Clustering"):
    df,data_scaled,labels,kmeans_model=run_kmeans(db_path="../timekeeping.db",n_clusters=k)
    #print(df,data_scaled,labels,kmeans_model)
    # print("data_scaled",data_scaled.shape)
    n_clusters=len(set(labels))

    st.write(f"**Number of Clusters**: {n_clusters}")
    #PCA for 2D visualization
    pca=PCA(n_components=2,random_state=42)
    pca_coords=pca.fit_transform(data_scaled)
    
    df_plot=pd.DataFrame({
        'PC1':pca_coords[:,0],
        'PC2':pca_coords[:,1],
        'cluster_label':labels})
    
    df_plot=pd.concat([df_plot,df[['project_no']].reset_index(drop=True)],axis=1)
    #print(df_plot.head())
    hover_data={'project_no':True}
    if 'financial_info' in df.columns: 
        hover_data['financial_info']=True
    
    fig_kmeans=px.scatter(
        df_plot,x='PC1',y='PC2',
        color='cluster_label',title='K-Means Clusters (2D PCA Projection)',
        labels={'PC1': 'Principal Component 1', 'PC2': 'Principal Component 2'},
        hover_data=hover_data
    )
    st.plotly_chart(fig_kmeans,use_container_width=True)

    st.subheader("All Projects with Cluster Labels and Financial Information")

    if 'financial_info' in df.columns:
        st.dataframe(df[['project_no', 'cluster_label', 'financial_info']])
    else:
        st.dataframe(df[['project_no', 'cluster_label']])

# create search box for projects
projects_df["display"]=projects_df["project_no"].astype(str)+" - "+projects_df["project_name"]
search_query=st.sidebar.text_input("Search Projects","")

# filter based on query
filtered_projects=(projects_df[projects_df["display"].str.contains(search_query,case=False,na=False)] if search_query else projects_df)

if filtered_projects.empty:
    st.sidebar.warning("No projects match your search.")
else:
    default_project_no="1901" # default project
    if default_project_no in filtered_projects["project_no"].astype(str).values:
        default_display=filtered_projects[filtered_projects["project_no"].astype(str)==default_project_no]["display"].iloc[0]
    else:default_display=None

    # project selection
    selected_proj=st.sidebar.selectbox("Select a Project",filtered_projects["display"].tolist(),index=filtered_projects["display"].tolist().index(default_display) if default_display else 0)
    selected_proj_no=selected_proj.split(" - ")[0].strip()
    st.write(f"### Work History for Project {selected_proj_no}")

    # from analysis time cost phase
    # get project summary
    kpi_df=get_project_summary(selected_proj_no,db_path="../timekeeping.db")

    if not kpi_df.empty:
        #print(kpi_df['project_captain'].iloc[0])
        #print(kpi_df['percent_complete'].iloc[0])
        #print(kpi_df['amount_left_to_bill'].iloc[0])
        captain=kpi_df["project_captain"].iloc[0]
        percent_complete_raw=kpi_df["percent_complete"].iloc[0]
        amount_left=kpi_df["amount_left_to_bill"].iloc[0]

        if pd.isnull(percent_complete_raw) or percent_complete_raw<=0:
            percent_complete_display="N/A"
        elif percent_complete_raw>=1.0:
            percent_complete_display="100%"
        else:
            percent_complete_display=f"{percent_complete_raw*100:.1f}%"
        
        # from analysis time cost phase
        df_hours=find_time_entries(selected_proj_no,db_path="../timekeeping.db")
        total_hours=df_hours["hours_worked"].sum()

        col1,col2,col3,col4=st.columns(4) # KPI columns
        col1.metric("Job Captain",captain if captain else "N/A")
        col2.metric("Completion %",percent_complete_display)
        col3.metric("Left to Bill",f"${amount_left:,.2f}" if pd.notnull(amount_left) and percent_complete_raw<1.0 else "Fully Billed")
        col4.metric("Total Hours Logged",f"{total_hours:,.1f}")
    else:
        st.warning("No KPI data available for this project.")

    # from analysis time cost phase
    agg_df=find_time_entries(selected_proj_no,db_path="../timekeeping.db")
    if not agg_df.empty:
        # create bar chart for work hours breakdown
        fig=px.bar(agg_df,x="month",y="hours_worked",color="type",title=f"Work Hours Breakdown per Month for Project {selected_proj_no}",labels={"month":"Month","hours_worked":"Hours Worked","type":"Work Type"},category_orders={"type":["Regular","Overtime","Weekend"]}) # bar chart
        st.plotly_chart(fig,use_container_width=True)

        st.markdown("---")
        st.subheader("Expenditure Forecast")

        with st.expander("Generate Forecast Report"):
            forecast_months=st.slider("Months to Forecast",min_value=1,max_value=3,value=3)

            if st.button("Run Forecast"):
                # from analysis forecast expenditure if enough data
                forecast_df=forecast_expenditure(selected_proj_no,forecast_months,db_path="../timekeeping.db")

                if forecast_df is not None:
                    # from analysis get monthyl expenditure
                    historical_df=get_monthly_expenditure(selected_proj_no,db_path="../timekeeping.db")

                    historical_df=historical_df.rename(columns={'expenditure':'Actual Expenditure'})
                    forecast_df=forecast_df.rename(columns={'forecast_expenditure':'Forecasted Expenditure'})

                    # combine historical and forecast data
                    combined_df=pd.concat([historical_df.set_index("ds"),forecast_df.set_index("ds")],axis=1).reset_index().rename(columns={'index':'Date'})

                    # line chart for actual/forecast expense
                    fig2=px.line(combined_df,x="ds",y=["Actual Expenditure","Forecasted Expenditure"],title=f"Forecasted Expenditure for Project {selected_proj_no}",labels={"value":"Expenditure ($)","variable":"Legend"},markers=True)
                    st.plotly_chart(fig2,use_container_width=True)

                else:
                    st.warning("Not enough data to generate a forecast.")


    st.markdown("---")
    st.subheader("Phase Analysis for This Project")
    with st.expander("View Time & Cost by Phase"):
        # phases we care about, all else are noise.
        phase_map={"BP":"Building Permit Drawings",
                   "DP":"Development Permit Drawings",
                   "CD":"Construction Documents",
                   "CA":"Construction Administration",
                   "D":"Design Phase",
                   "ADM":"Admin",
                   "DP 1a":"Development Permit Drawings 1a",
                   "DP 1b":"Development Permit Drawings 1b",
                   "DP 1c":"Development Permit Drawings 1c",
                   "DP 2a":"Development Permit Drawings 2a",
                   "DP 2b":"Development Permit Drawings 2b",
                   "DP 2c":"Development Permit Drawings 2c",
                   "BP 1a":"Building Permit Drawings 1a",
                   "BP 1b":"Building Permit Drawings 1b",
                   "BP 1c":"Building Permit Drawings 1c",
                   "BP 2a":"Building Permit Drawings 2a",
                   "BP 2b":"Building Permit Drawings 2b",
                   "BP 2c":"Building Permit Drawings 2c",
                   "BP 3a":"Building Permit Drawings 3a",
                   "BP 3b":"Building Permit Drawings 3b",
                   "BP 3c":"Building Permit Drawings 3c",
                   "WD":"Working Drawings",
                   "nan":"Empty Work Code"}

        # from analysis load phase data
        df_phases=load_phase_data(db_path="../timekeeping.db",phase_map=phase_map)

        # only care about this project
        df_phases_selected=df_phases[df_phases["project_no"]==selected_proj_no]
        
        if df_phases_selected.empty:
            st.warning("No phase data for this project")
        else:
            # from analysis, time cost phase . py
            phase_summary=summarize_time_and_cost_by_phase(df_phases_selected)

            # create bar chart
            fig_phase=px.bar(phase_summary,x='phase',y='total_cost',hover_data=['total_hours','total_cost'],title=f"Time & Cost by Phase for Project {selected_proj_no}",labels={'phase':'Project Phase','total_cost':'Total Cost ($)'},color='total_cost',color_continuous_scale=px.colors.sequential.Viridis)
            fig_phase.update_traces(texttemplate='%{y:.2f}',textposition='outside')
            fig_phase.update_layout(uniformtext_minsize=8,uniformtext_mode='hide')
            st.plotly_chart(fig_phase,use_container_width=True)

            # pie chart for cost distribution
            fig_pie=px.pie(phase_summary,names='phase',values='total_cost',title=f"Cost Distribution by Phase for Project {selected_proj_no}",color='phase',color_discrete_sequence=px.colors.qualitative.Plotly) # pie chart
            st.plotly_chart(fig_pie,use_container_width=True)

            # table overivew
            st.dataframe(phase_summary)
        
        st.subheader("Aggregated Phase Data Across ALL Projects")

        filtered_df_phases=df_phases[df_phases['phase']!="Empty Work Code"] # filter empty work codes

        all_phase_summary=(filtered_df_phases.groupby('phase').agg(total_hours=('hours_worked','sum'),total_cost=('cost','sum')).reset_index())

        # total cost by phase pie chart
        fig_all=px.pie(all_phase_summary,names='phase',values='total_cost',title="Overall Cost Distribution by Phase (All Projects)",color='phase',color_discrete_sequence=px.colors.qualitative.Plotly)
        st.plotly_chart(fig_all,use_container_width=True)

conn.close()
