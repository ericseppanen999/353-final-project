

import streamlit as st

st.title("Welcome to the Dashboard!")
st.write("This is the landing page of the app.")

if st.button("Home"):
    st.switch_page("main.py")
if st.button("Timekeeping Tables"):
    st.switch_page("pages/timekeeping_tables.py")

    