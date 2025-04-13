import streamlit as st



def show_buttons(page_title, page_subtitle):
    st.set_page_config(layout="wide")

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
        st.title(page_title)
        st.subheader(page_subtitle)

    st.text("")

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

