import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import matplotlib.pyplot as plt




st.set_page_config(page_title="Dashboard Home", layout="wide")

#for bigger buttons
st.markdown(
    """
    <style>
        .stButton>button {
            font-size: 18px !important;
            padding: 12px 24px !important;
            width: 100% !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

#makes the logo and title side by side
col_logo, col_title = st.columns([0.15, 1])#adjust the first value to change logo size



with col_logo:
    st.text("")
    st.text("")
    st.image("assets/logo.png", width=180)#adjust width to fit logo
    
with col_title:
    st.title("Welcome to the RWA Analytics Dashboard!")
    st.subheader("Your all-in-one timekeeping and analytics tool.")


st.text("")
st.write(
    "Navigate through different sections to explore statistics and data. Use the buttons below to get started!"
)

#make closely spaced columns for buttons
col1, col2, col3 = st.columns([1, 0.8, 1])  

with col1:
    if st.button("Home"):
        st.switch_page("main.py")
    if st.button("Employee Analysis"):
        st.switch_page("pages/Employee-Analysis.py")

with col2:
    if st.button("Project Level Insights"):
        st.switch_page("pages/Project-Level-Insights.py")
    if st.button("Monthly Hours Analysis"):
        st.switch_page("pages/Monthly-Hours-Analysis.py")

with col3:
    if st.button("General Tables"):
        st.switch_page("pages/General-Tables.py")


col_left, col_center, col_right = st.columns([1, 2, 1])

with col_center:
    st.text("")
    st.text("")
    st.image("assets/image.jpg", width=1000)
    st.text("")
    st.text("")

col_spacer1, col_info1, col_spacer2, col_info2, col_spacer3 =st.columns([0.2, 1,0.4, 1, 0.2])
with col_info1:
    st.text("")
    st.markdown(
        """
        ### About This Dashboard

        This interactive dashboard was created as part of the CMPT 353 at Simon Fraser University in the Spring 2025 semester. The project focuses on building a complete data pipeline to convert raw organizational data from RWA Architecture Group into meaningful business insights. We collected and cleaned timekeeping and project records, stored them in a SQLite database, and developed visual analytics using Streamlit. The result is a user-friendly interface that provides a streamlined view of workforce and project data for internal decision-making and performance tracking.
        """
    )

with col_info2:
    st.text("")
    st.markdown(
        
        """
        ### Project Info

        - Course: CMPT 353 – Data Science
        - Group Members: Annie Boltwood & Eric Seppanen
        - Semester: Spring 2025
        - Tools Used: Python, SQLite, Streamlit, pandas, plotly
        - Real-World Focus: Designed for RWA Architecture Group
        """
        
    )
    st.text("")
    st.text("")

st.markdown("---")
st.write("For support or more details, contact the admin.")