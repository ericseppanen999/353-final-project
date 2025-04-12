import streamlit as st
import pandas as pd
import plotly.express as px
from analysis.burnout import get_burnout_analysis

st.title("Employee Burnout Risk Dashboard")
st.markdown("""
This dashboard shows burnout risk scores for employees based on their time entry data.
The analysis factors in daily overtime, weekend work frequency, and monthly excess hours above a reasonable baseline (default ~150 hours/month).
""")

# sidebar inputs
st.sidebar.header("Settings")
db_path=st.sidebar.text_input("Database path",value="../timekeeping.db")
baseline=st.sidebar.number_input("Monthly Baseline (hours)",value=7.5*5*4,step=10.0,format="%.0f")
top_n=st.sidebar.slider("Show Top N Employees",min_value=5,max_value=30,value=10)

# load burnout data
with st.spinner("Loading burnout metrics..."):
    burnout_df=get_burnout_analysis(db_path,baseline)

if burnout_df.empty:
    st.error("No time entries found or unable to compute burnout metrics.")
else:
    # sort and filter top n
    burnout_df=burnout_df.sort_values('burnout_score',ascending=False).reset_index(drop=True)
    
    # add a new column for bar colors based on burnout_score
    burnout_df["bar_color"]=burnout_df["burnout_score"].apply(lambda x:"red" if x>1 else "white")
    
    # bar chart for top n employees
    top_burnout=burnout_df.head(top_n)
    fig=px.bar(top_burnout,
               x='name',
               y='burnout_score',
               hover_data={'avg_daily_overtime':True,
                           'weekend_frequency':':.2f',
                           'avg_monthly_excess':':.1f'},
               labels={'name':'Employee','burnout_score':'Burnout Score'},
               title=f"Top {top_n} Employees by Burnout Score")
    # update bar colors based on our computed list
    fig.update_traces(marker_color=top_burnout["bar_color"].tolist())
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig,use_container_width=True)
    
    # scatter plot for overtime vs weekend frequency
    fig2=px.scatter(burnout_df,x='avg_daily_overtime',y='weekend_frequency',
                    size='avg_monthly_excess',color='burnout_score',hover_name='name',
                    labels={'avg_daily_overtime':'Avg Daily Overtime (hrs)',
                            'weekend_frequency':'Weekend Work Frequency'},
                    title="Burnout Risk: Overtime vs. Weekend Work (size = Monthly Excess)")
    st.plotly_chart(fig2,use_container_width=True)
    
    st.subheader("Burnout Risk Scores for Employees")
    st.dataframe(burnout_df[['employee_id','name','total_days','avg_daily_hours','avg_daily_overtime',
                              'weekend_frequency','avg_monthly_excess','burnout_score']])
    
    st.markdown("### Detailed Burnout Analysis")
    st.write("The burnout score is a composite metric defined as:")
    st.latex(r"\text{burnout\_score} = \text{avg\_daily\_overtime} + 2 \times \text{weekend\_frequency} + \frac{\text{avg\_monthly\_excess}}{50}")
    st.markdown("""
    - **Avg Daily Overtime:** Average hours worked beyond 8 hours per day.
    - **Weekend Frequency:** Proportion of working days that fall on weekends.
    - **Avg Monthly Excess:** Average extra monthly hours worked above the baseline (e.g., 150 hours).
    """)
