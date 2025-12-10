import streamlit as st
import yaml
from yaml.loader import SafeLoader
from components.container import card_container

def show():
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Executive Overview")
    with col2:
        st.markdown(f"<div style='text-align: right; padding-top: 20px;'>Welcome, <strong>{st.session_state['name']}</strong></div>", unsafe_allow_html=True)
    # KPIs Display
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with card_container(key="kpi_metric1"):
            st.metric("Dummy Value", "$123")
    
    with col2:
        with card_container(key="kpi_metric2"):
            st.metric("Dummy Value 2", "12.3%")

    with col3:
        with card_container(key="kpi_metric3"):
            st.metric("Dummy Value 3", "1234.5%")
