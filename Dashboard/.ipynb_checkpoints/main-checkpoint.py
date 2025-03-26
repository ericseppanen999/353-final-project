
import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import streamlit as st

#conn = sqlite3.connect('../timekeeping.db')

st.title("Welcome to the Dashboard!")
st.write("This is the landing page of the app.")

if st.button("Home"):
    st.switch_page("main.py")
if st.button("Monthly Stats"):
    st.switch_page("pages/monthly_stats.py")
if st.button("Timekeeping Tables"):
    st.switch_page("pages/timekeeping_tables.py")

    
