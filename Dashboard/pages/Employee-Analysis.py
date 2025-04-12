import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import ttest_1samp,shapiro,wilcoxon,mannwhitneyu
from analysis.employee_clusters import load_annual_usage,cluster_data
from analysis.senior_trends import get_top10_trends
from analysis.seasonality import load_monthly_hours,month_to_season
from analysis.burnout import get_burnout_analysis
from numpy import percentile


from utils.header_navigation import show_buttons#CUSTOM HEADER (utils folder)

show_buttons("Employee Analysis", "Insights into employee behaviour and productivity.")

df=load_annual_usage()
st.header("Usage Patterns:")
st.header("Top 10 Project vs. Overhead Workers")

# top 10 billable vs non billable
top_bill=df.nlargest(10,'billable_hours').sort_values('billable_hours')
fig1=px.bar(top_bill,x='billable_hours',y='name',orientation='h',
    title='Top 10 Project Workers (by Billable Hours)',
    labels={'billable_hours':'Billable Hours','name':'Employee'},
    hover_data=['non_billable_hours'],
    color='billable_hours',color_continuous_scale='Blues')

fig1.update_layout(
    xaxis=dict(showgrid=False,showticklabels=False,zeroline=False,visible=False),
    yaxis=dict(showgrid=False,zeroline=False))

top_non=df.nlargest(10,'non_billable_hours').sort_values('non_billable_hours') # top 10 non-billable workers
fig2=px.bar(
    top_non,
    x='non_billable_hours',y='name',orientation='h',
    title='Top 10 Overhead Workers (by Non-Billable Hours)',
    labels={'non_billable_hours':'Non-Billable Hours','name':'Employee'},
    hover_data=['billable_hours'],
    color='non_billable_hours',color_continuous_scale='Reds')

fig2.update_layout(
    xaxis=dict(showgrid=False,showticklabels=False,zeroline=False,visible=False),
    yaxis=dict(showgrid=False,zeroline=False))

col1,col2=st.columns(2)
with col1:
    st.plotly_chart(fig1,use_container_width=True)
with col2:
    st.plotly_chart(fig2,use_container_width=True)

st.header("Utilization Clusters")

# k selection for interactivity
k=st.sidebar.slider("Number of clusters (k)",2,6,2) # Cluster slider
# from analysis.employee_clusters, import cluster_data
clustered,km=cluster_data(df,n_clusters=k)

# colours that are more distint and vibrant
custom_colours=["#FF9999","#66B3FF","#99FF99","#FFCC99","#FFD700"]
df['cluster']=df['cluster'].astype(str)

# create scatters
fig=px.scatter(clustered,x='billable_pct',y='log_total_hours',color='cluster',
    color_discrete_sequence=px.colors.qualitative.Set2,
    hover_data=['name','position','total_hours'],
    title="% Billable vs. Log(Total Hours)")
#print(clustered['is_senior'].unique())
#print(clustered['is_senior'].value_counts())
mask_s=clustered.is_senior==1
# add scatter for seniors
fig.add_trace(go.Scatter(x=clustered.loc[mask_s,'billable_pct'],y=clustered.loc[mask_s,'log_total_hours'],mode='markers',marker=dict(symbol='diamond-open',size=12,line=dict(width=2,color='gold')),name='Senior',hoverinfo='skip'))
st.plotly_chart(fig,use_container_width=True)

st.subheader("Cluster Composition")
summary=clustered.groupby('cluster').agg(count=('employee_id','count'),avg_billable_pct=('billable_pct','mean'),avg_total_hours=('total_hours','mean')).round(2).reset_index()
summary['avg_billable_pct']=(summary['avg_billable_pct']*100).astype(str)+'%'
st.dataframe(summary)

st.header("Role Evolution Over Time:")
# from senior trends
trends_df,monthly_data=get_top10_trends()

#print(trends_df.columns)

cols=st.columns(2)
# plot trends for each employee
for idx,row in trends_df.iterrows():
    # get employee id, name, slope, intercept, p-value, and mean index
    eid,name,slope,intercept,p,mean_idx=row[['employee_id','name','slope','intercept','p_value','mean_idx']]
    df_ts=monthly_data[eid]
    col=cols[idx%2]
    with col:
        st.subheader(name)
        fig2=go.Figure()
        fig2.add_trace(go.Scatter(x=df_ts.month_dt,y=df_ts.billable_pct,mode='markers+lines'))
        fig2.add_trace(go.Scatter(x=df_ts.month_dt,y=slope*(df_ts.m_idx-mean_idx)+intercept,mode='lines',line=dict(dash='dash',color='red'),name='Trend'))
        fig2.update_layout(height=300,yaxis_tickformat='.0%',xaxis_title='Month',yaxis_title='Billable %',showlegend=False)
        st.plotly_chart(fig2,use_container_width=True)
        st.write(f"Slope: **{slope*12:.3f}** per year | p-value: **{p:.3f}**")

slopes=trends_df['slope'].values
#t_stat,p_two_sided=ttest_1samp(slopes,0)
#p_one_sided=p_two_sided/2 if t_stat<0 else 1-p_two_sided/2
#mean_slope=slopes.mean()

st.write("")

st.write("**Slope Analysis:**")

st.write("")

# test for normality
stat,p=shapiro(slopes)
st.write(f"**Shapiro-Wilk test:** W={stat:.3f},p={p:.3f}")
if p>0.05:
    st.write("Fail to reject H₀: data **looks normal** (p>0.05).")
else:
    st.write("Reject H₀: data **not normal** (p≤0.05).")

st.write("")

# test for median slope
stat,pw=wilcoxon(slopes,alternative='less')
#print(pw)
st.write(f"**Wilcoxon signed-rank test (median<0):** p={pw:.3f}")
if pw<0.05:
    st.write("The median slope is significantly below zero (p<0.05). There is evidence that the slope is decreasing, i.e. employees are declining in billable work.")
else:
    st.write("No significant evidence that the median slope is below zero.")

st.header("Burnout Analysis ")

    
st.markdown("**Detailed Burnout Analysis:**")
st.write("The burnout score is a composite metric defined as:")
st.latex(r"\text{burnout\_score} = \text{avg\_daily\_overtime} + 2 \times \text{weekend\_frequency} + \frac{\text{avg\_monthly\_excess}}{50} + \frac{\text{total\_days}}{10000}")
st.latex(r"\text{burnout\_plus} = \frac{\text{burnout\_score}-\mu}{\sigma} \times 15 + 100")

st.markdown("""
- **avg_daily_overtime**: Average daily overtime hours worked by the employee.
- **weekend_frequency**: Proportion of days worked on weekends.
- **avg_monthly_excess**: Average monthly excess hours worked above the baseline (e.g., 150 hours).
- **total_days**: Total number of days worked by the employee.
- **burnout_score**: A composite score indicating the risk of burnout, calculated using the formula above.
- **burnout_plus**: A normalized score indicating the relative burnout risk compared to the average employee, calculated using the z-score formula.
""")
# sidebar inputs
st.sidebar.header("Settings")
db_path=st.sidebar.text_input("Database path",value="../timekeeping.db")
baseline=st.sidebar.number_input("Monthly Baseline (hours)",value=7.5*5*4,step=10.0,format="%.0f")
top_n=st.sidebar.slider("Show Top N Employees",min_value=5,max_value=30,value=10)

# load burnout data
with st.spinner("Loading burnout metrics..."):
    burnout_df=get_burnout_analysis(db_path,baseline)
    #print(burnout_df.columns)
    #print(burnout_df.head())
if burnout_df.empty:
    st.error("No time entries found or unable to compute burnout metrics.")
    #print("EMPTY")
else:
    # sort and filter top n
    burnout_df=burnout_df.sort_values('burnout_score',ascending=False).reset_index(drop=True)
    
    # add a new column for bar colors based on burnout_score
    burnout_df["bar_color"]=burnout_df["burnout_plus"].apply(lambda x:"red" if x>130 else "white")
    
    # bar chart for top n employees
    top_burnout=burnout_df.head(top_n)
    #print(len(top_burnout))
    fig=px.bar(top_burnout,x='name',y='burnout_plus',
               hover_data={'avg_daily_overtime':True,
                           'weekend_frequency':':.2f',
                           'avg_monthly_excess':':.1f'},
               labels={'name':'Employee','burnout_score':'Burnout Score'},
               title=f"Top {top_n} Employees by Burnout Plus")
    fig.add_shape(
    type="line",
    x0=-0.5,
    x1=len(top_burnout)-0.5,
    y0=130,
    y1=130,
    line=dict(color="red", width=2, dash="dot"),
    )

    fig.add_annotation(x=len(top_burnout)-1,y=130,
        text="High Burnout Threshold (130)",
        showarrow=False,yshift=10,font=dict(color="red")
    )
    # update bar colors based on our computed list
    fig.update_traces(marker_color=top_burnout["bar_color"].tolist())
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig,use_container_width=True)
    st.markdown("""
    **To Intepret:** Consider that 100 is the firm's average, 115 is 1 standard deviation above the mean, and 130 is 2 standard deviations above the mean.
    A score of 130 or above indicates a high risk of burnout. The z-score is a standardized score that indicates how many standard deviations an element is from the mean.
    Please note that this metric is not diagnostic and should be used with the help of other assessments.
    """)
    # scatter plot for overtime vs weekend frequency
    fig2=px.scatter(burnout_df,x='avg_daily_overtime',y='weekend_frequency',
                    size='avg_monthly_excess',color='burnout_score',hover_name='name',
                    labels={'avg_daily_overtime':'Avg Daily Overtime (hrs)',
                            'weekend_frequency':'Weekend Work Frequency'},
                    title="Burnout Risk: Overtime vs. Weekend Work (size = Monthly Excess)")
    st.plotly_chart(fig2,use_container_width=True)
    
    st.subheader("Burnout Risk Scores for Employees")
    st.dataframe(burnout_df[['employee_id','name','total_days','avg_daily_hours','avg_daily_overtime','weekend_frequency','avg_monthly_excess','burnout_score']])


st.header("Seasonality Trends")

# from seasonality analysis file
df=load_monthly_hours()
df['position']=df['position'].fillna("Unknown")

# filter by position and seniority
# get unique positions and seniority
#print(df['position'].unique())
#print(df['is_senior'].unique())
positions=['All']+sorted(df['position'].unique().tolist())
#print(positions)
sel_position=st.sidebar.selectbox("Filter by Position",positions)
sel_senior=st.sidebar.selectbox("Filter by Seniority",['All','Senior','Junior'])

# filter data based on selection
df_filt=df.copy()
if sel_position!='All':
    df_filt=df_filt[df_filt['position']==sel_position]
if sel_senior=='Senior':
    df_filt=df_filt[df_filt['is_senior']==1]
elif sel_senior=='Junior':
    df_filt=df_filt[df_filt['is_senior']==0]


#print(len(df_filt))
if df_filt.empty:
    st.warning("No data for selected filters.")
    st.stop()


def percentile(series,pct_val):
    #print("series",series)
    #print("pct_val",pct_val)
    return np.percentile(series,pct_val)

monthly_stats=(
    df_filt.groupby('month_dt').agg(
        median_hours=('total_hours','median'),
        pct_75=('total_hours',lambda x:percentile(x,75)),pct_25=('total_hours',lambda x:percentile(x,25))
        ).reset_index())

fig=px.line(
    monthly_stats,
    x='month_dt',y='median_hours',
    title="Median Monthly Hours per Employee",
    labels={'month_dt':'Month','median_hours':'Median Hours'}
)

fig.add_trace(go.Scatter(
    x=monthly_stats['month_dt'],
    y=monthly_stats['pct_75'],
    mode='lines',name='75th percentile',
    line=dict(dash='dash')
))
fig.add_trace(go.Scatter(
    x=monthly_stats['month_dt'],
    y=monthly_stats['pct_25'],
    mode='lines',name='25th percentile',
    line=dict(dash='dash')
))

fig.update_layout(
    xaxis_title="Year",
    yaxis_title="Hours",
    showlegend=True
)
st.plotly_chart(fig,use_container_width=True)

st.markdown("### Seasonality Test: Seniors vs. Juniors ###")

# from seasonality analysis file
monthly=load_monthly_hours()
monthly['season']=monthly['month_dt'].dt.month.apply(month_to_season)
monthly['seniority']=monthly['is_senior'].map({0:'Junior',1:'Senior'})
df_filt=monthly.copy()

# calculate median hours by employee, seniority, and season
emp_season=(
    monthly.groupby(['employee_id','seniority','season'])['total_hours'].median().reset_index(name='emp_season_med')
)

# calculate median hours by seniority and season
seasonal=(
    emp_season.groupby(['seniority','season'])['emp_season_med'].median().reset_index(name='season_median_hours')
)

st.write("**Seasonal Median Hours by Seniority**")
st.dataframe(seasonal)

# calculate total hours by season
season_totals=(
    df_filt.groupby('season')['total_hours'].sum().reset_index(name="total_season_hours")
)

# plot total hours by season
st.subheader("Total Hours by Season")
fig_seasons=px.bar(
    season_totals,
    x='season',y='total_season_hours',
    title="Total Hours Aggregated by Season",
    labels={'season':'Season','total_season_hours':'Total Hours'},
    color='season'
)
st.plotly_chart(fig_seasons,use_container_width=True)

# Mann-Whitney U test for each season
results=[]
for season in ["Winter","Spring","Summer","Fall"]:
    grp=emp_season[emp_season['season']==season]
    # note emp_season_med is employee season median hours
    seniors=grp[grp.seniority=='Senior']['emp_season_med']
    juniors=grp[grp.seniority=='Junior']['emp_season_med']
    if len(seniors)>=3 and len(juniors)>=3:
        stat,p=mannwhitneyu(seniors,juniors,alternative='less')
    else:
        #print("Insufficient data for",season)
        #print(seniors,juniors)
        # why
        stat,p=np.nan,np.nan
    results.append({'season':season,'U_stat':stat,'p_value':p})

res_df=pd.DataFrame(results)
#print(res_df)
#print(res_df['significant']=res_df['p_value']<0.05)
st.subheader("Mann-Whitney U Test Results")
st.dataframe(res_df.style.format({'p_value':'{:.3f}'}))

st.subheader("Interpretation")
for r in results:
    season,p=r['season'],r['p_value']
    if np.isnan(p):
        st.write(f"- {season}: Insufficient data to test.")
    elif p<0.05:
        st.write(f"- {season}: Seniors work significantly fewer hours than juniors (p={p:.3f}).")
    else:
        st.write(f"- {season}: No significant difference (p={p:.3f}).")
