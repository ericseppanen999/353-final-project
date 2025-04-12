import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import ttest_1samp,shapiro,wilcoxon,mannwhitneyu
from analysis.employee_clusters import load_annual_usage,cluster_data
from analysis.senior_trends import get_top10_trends
from analysis.seasonality import load_monthly_hours,load_seasonal_hours,month_to_season

st.set_page_config(layout="wide")
st.title("Employee Utilization Dashboard")

df=load_annual_usage()
st.header("Top 10 Project vs. Overhead Workers")
top_bill = df.nlargest(10, 'billable_hours').sort_values('billable_hours')
fig1 = px.bar(
    top_bill,
    x='billable_hours',
    y='name',
    orientation='h',
    title='Top 10 Project Workers (by Billable Hours)',
    labels={'billable_hours':'Billable Hours','name':'Employee'},
    hover_data=['non_billable_hours'],
    color='billable_hours',
    color_continuous_scale='Blues'
)
fig1.update_layout(
    #yaxis={'categoryorder':'total ascending'},
    xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
    yaxis=dict(showgrid=False, zeroline=False)
)

# Overhead Workers
top_non = df.nlargest(10, 'non_billable_hours').sort_values('non_billable_hours')
fig2 = px.bar(
    top_non,
    x='non_billable_hours',
    y='name',
    orientation='h',
    title='Top 10 Overhead Workers (by Non‑Billable Hours)',
    labels={'non_billable_hours':'Non‑Billable Hours','name':'Employee'},
    hover_data=['billable_hours'],
    color='non_billable_hours',
    color_continuous_scale='Reds'
)
fig2.update_layout(
    #yaxis={'categoryorder':'total ascending'},
    xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
    yaxis=dict(showgrid=False, zeroline=False)
)

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig1, use_container_width=True)
with col2:
    st.plotly_chart(fig2, use_container_width=True)

st.header("1. Utilization Clusters")

k=st.sidebar.slider("Number of clusters (k)",2,6,2)
clustered,km=cluster_data(df,n_clusters=k)

custom_colours=["#FF9999","#66B3FF","#99FF99","#FFCC99","#FFD700"]
df['cluster']=df['cluster'].astype(str)

fig=px.scatter(clustered,x='billable_pct',y='log_total_hours',color='cluster',color_discrete_sequence=px.colors.qualitative.Set2,hover_data=['name','position','total_hours'],title="% Billable vs. Log(Total Hours)")
mask_s=clustered.is_senior==1
fig.add_trace(go.Scatter(x=clustered.loc[mask_s,'billable_pct'],y=clustered.loc[mask_s,'log_total_hours'],mode='markers',marker=dict(symbol='diamond-open',size=12,line=dict(width=2,color='gold')),name='Senior',hoverinfo='skip'))
st.plotly_chart(fig,use_container_width=True)

st.subheader("Cluster Composition")
summary=clustered.groupby('cluster').agg(count=('employee_id','count'),avg_billable_pct=('billable_pct','mean'),avg_total_hours=('total_hours','mean')).round(2).reset_index()
summary['avg_billable_pct']=(summary['avg_billable_pct']*100).astype(str)+'%'
st.dataframe(summary)

st.header("2. Role Change Over Time: Top 10 Billable Employees")
trends_df,monthly_data=get_top10_trends()

cols=st.columns(2)
for idx,row in trends_df.iterrows():
    eid,name,slope,intercept,p,mean_idx=row[['employee_id','name','slope','intercept','p_value','mean_idx']]
    df_ts=monthly_data[eid]
    col=cols[idx%2]
    with col:
        st.subheader(name)
        fig2=go.Figure()
        fig2.add_trace(go.Scatter(x=df_ts.month_dt,y=df_ts.billable_pct,mode='markers+lines'))
        fig2.add_trace(go.Scatter(x=df_ts.month_dt,y=slope*(df_ts.m_idx-mean_idx)+intercept,mode='lines',line=dict(dash='dash'),name='Trend'))
        fig2.update_layout(height=300,yaxis_tickformat='.0%',xaxis_title='Month',yaxis_title='Billable %',showlegend=False)
        st.plotly_chart(fig2,use_container_width=True)
        st.write(f"Slope: **{slope*12:.3f}** per year | p-value: **{p:.3f}**")
slopes=trends_df['slope'].values
t_stat,p_two_sided=ttest_1samp(slopes,0)
p_one_sided=p_two_sided/2 if t_stat<0 else 1-p_two_sided/2
mean_slope=slopes.mean()

stat,p_sw=shapiro(slopes)
st.write(f"Shapiro–Wilk test: W={stat:.3f},p={p_sw:.3f}")
if p_sw>0.05:
    st.write("Fail to reject H₀: data **looks normal** (p>0.05).")
else:
    st.write("Reject H₀: data **not normal** (p≤0.05).")

stat,p_w=wilcoxon(slopes,alternative='less')
st.write(f"Wilcoxon signed‑rank test (median<0): p={p_w:.3f}")
if p_w<0.05:
    st.write("⇒ The median slope is significantly below zero (p<0.05).")
else:
    st.write("⇒ No significant evidence that the median slope is below zero.")


st.header("4.4 Seasonality Trends")

# 1) Load data
df = load_monthly_hours()

# 2) Sidebar filters
# 2) Sidebar filters
# Fill missing positions with "Unknown"
df['position'] = df['position'].fillna("Unknown")

positions = ['All'] + sorted(df['position'].unique().tolist())
sel_position = st.sidebar.selectbox("Filter by Position", positions)
sel_senior = st.sidebar.selectbox("Filter by Seniority", ['All','Senior','Junior'])

df_filt = df.copy()
if sel_position != 'All':
    df_filt = df_filt[df_filt['position']==sel_position]
if sel_senior == 'Senior':
    df_filt = df_filt[df_filt['is_senior']==1]
elif sel_senior == 'Junior':
    df_filt = df_filt[df_filt['is_senior']==0]

if df_filt.empty:
    st.warning("No data for selected filters.")
    st.stop()

# 3) Compute average monthly hours across employees
monthly_stats = (
    df_filt.groupby('month_dt')
           .agg(
             median_hours=('total_hours','median'),
             pct_75=('total_hours', lambda x: x.quantile(0.75)),
             pct_25=('total_hours', lambda x: x.quantile(0.25))
           )
           .reset_index()
)

import plotly.graph_objects as go


fig = px.line(
    monthly_stats,
    x='month_dt',
    y='median_hours',
    title="Median Monthly Hours per Employee",
    labels={'month_dt':'Month','median_hours':'Median Hours'}
)

fig.add_trace(go.Scatter(
    x=monthly_stats['month_dt'],
    y=monthly_stats['pct_75'],
    mode='lines',
    name='75th percentile',
    line=dict(dash='dash')
))
fig.add_trace(go.Scatter(
    x=monthly_stats['month_dt'],
    y=monthly_stats['pct_25'],
    mode='lines',
    name='25th percentile',
    line=dict(dash='dash')
))

fig.update_layout(
    xaxis_title="Year",
    yaxis_title="Hours",
    showlegend=True
)
st.plotly_chart(fig, use_container_width=True)

st.header("Seasonality Test: Seniors vs. Juniors")

st.header("Seasonality Test: Seniors vs. Juniors (Per‑Employee Seasonal Medians)")

# 1) Load raw monthly data
monthly = load_monthly_hours()

# 2) Assign season & seniority
monthly['season']    = monthly['month_dt'].dt.month.apply(month_to_season)
monthly['seniority'] = monthly['is_senior'].map({0:'Junior',1:'Senior'})
df_filt=monthly.copy()
# 3) Compute per-employee median hours per season
emp_season = (
    monthly
      .groupby(['employee_id','seniority','season'])['total_hours']
      .median()
      .reset_index(name='emp_season_med')
)

# 4) Display the per-employee medians (optional)
#st.subheader("Sample of Per‑Employee Seasonal Medians")
#st.write(emp_season.head(10))

# 5) Cohort medians by seniority & season
seasonal = (
    emp_season
      .groupby(['seniority','season'])['emp_season_med']
      .median()
      .reset_index(name='season_median_hours')
)
st.subheader("Seasonal Median Hours by Seniority")
st.dataframe(seasonal)

# --- NEW: Aggregate Total Hours by Season ---
# Aggregate the total hours per season using the filtered data.
season_totals = (
    df_filt.groupby('season')['total_hours']
            .sum()
            .reset_index(name="total_season_hours")
)
st.subheader("Total Hours by Season")
fig_seasons = px.bar(
    season_totals,
    x='season',
    y='total_season_hours',
    title="Total Hours Aggregated by Season",
    labels={'season': 'Season', 'total_season_hours': 'Total Hours'},
    color='season'
)
st.plotly_chart(fig_seasons, use_container_width=True)

# 5) Mann–Whitney U test on those per‑employee medians
results = []
for season in ["Winter", "Spring", "Summer", "Fall"]:
    grp = emp_season[emp_season['season'] == season]
    seniors = grp[grp.seniority == 'Senior']['emp_season_med']
    juniors = grp[grp.seniority == 'Junior']['emp_season_med']
    if len(seniors) >= 3 and len(juniors) >= 3:
        stat, p = mannwhitneyu(seniors, juniors, alternative='less')
    else:
        stat, p = np.nan, np.nan
    results.append({'season': season, 'U_stat': stat, 'p_value': p})

res_df = pd.DataFrame(results)
st.subheader("Mann–Whitney U Test Results")
st.dataframe(res_df.style.format({'p_value': '{:.3f}'}))

# 6) Interpretation
st.subheader("Interpretation")
for r in results:
    season, p = r['season'], r['p_value']
    if np.isnan(p):
        st.write(f"- {season}: Insufficient data to test.")
    elif p < 0.05:
        st.write(f"- {season}: Seniors work significantly fewer hours than juniors (p={p:.3f}).")
    else:
        st.write(f"- {season}: No significant difference (p={p:.3f}).")