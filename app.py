import streamlit as st
import pandas as pd 
import plotly.express as px 
import plotly.graph_objects as go 
from plotly.subplots import make_subplots 
import numpy as np

st.set_page_config(
    page_title = "Water Utilities Dashboard",
    layout = "wide",
    initial_sidebar_state = "expanded"
)

#CSS will go here 
st.markdown("""
<style>
    .main-header {
        font-size: 42px;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 20px;
    }
    .sub-header {
        font-size: 24px;
        color: #2c3e50;
        padding: 10px 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data(): 
    all_fin_service = pd.read_csv('data/all_fin_service.csv')
    all_national = pd.read_csv('data/all_national.csv')
    billing = pd.read_csv('data/billing.csv')
    production = pd.read_csv('data/production.csv')
    s_access = pd.read_csv('data/s_access.csv')
    s_service = pd.read_csv('data/s_service.csv')
    w_access = pd.read_csv('data/water_access.csv')
    w_service = pd.read_csv('data/water_service.csv')

 # Parse dates
    all_fin_service['date_MMYY'] = pd.to_datetime(all_fin_service['date_MMYY'], format='%b/%y')
    all_national['date_YY'] = pd.to_datetime(all_national['date_YY'], format='%Y')
    billing['date_MMYY'] = pd.to_datetime(billing['date_MMYY'], format='%b/%y')
    production['date_YYMMDD'] = pd.to_datetime(production['date_YYMMDD'], format='%Y/%m/%d')
    s_access['date_YY'] = pd.to_datetime(s_access['date_YY'], format='%Y')
    s_service['date_MMYY'] = pd.to_datetime(s_service['date_MMYY'], format='%b/%y')
    w_access['date_YY'] = pd.to_datetime(w_access['date_YY'], format='%Y')
    w_service['date_MMYY'] = pd.to_datetime(w_service['date_MMYY'], format='%b/%y')

    return {
        'data/all_fin_service': all_fin_service,
        'data/all_national': all_national,
        'data/billing': billing,
        'data/production': production,
        'data/s_access': s_access,
        'data/s_service': s_service,
        'data/water_access': w_access,
        'data/water_service': w_service
    }

data = load_data()

# Sidebar 
with st.sidebar:
    st.title("Navigation")

    page = st.radio(
        "Select a Page", 
        [
            "Executive Overview", 
            "Financial Performance",
            "Service Delivery",
            "Operations & Production",
            "Access" 
        ]
    )

    st.markdown("---")
    st.subheader("Global Filters")

#Filtering for countries
    all_countries = set() 
    for df in data.values(): 
        if "country" in df.columns: 
            all_countries.update(df["country"].unique())

    selected_countries = st.multiselect( 
        "Select Countries", 
        options=sorted(all_countries),
        default=sorted(all_countries)
    )

    all_years = []
    for df_name, df in data.items(): 
        if "date_YY" in df.columns: 
            all_years.extend(df["date_YY"].dt.year.unique())
        elif "date_MMYY" in df.columns: 
            # FIXED TYPOS
            all_years.extend(df["date_MMYY"].dt.year.unique())
        elif "date_YYMMDD" in df.columns: 
            all_years.extend(df["date_YYMMDD"].dt.year.unique())
    
    if all_years:
        year_range = st.slider(
            "Select Year Range", 
            min_value=int(min(all_years)),
            max_value=int(max(all_years)),
            value=(int(min(all_years)), int(max(all_years)))
        )

#For a report: 
with st.sidebar:
    st.download_button(
        label="📄 Download Report PDF",
        data=open("report.pdf", "rb").read(),
        file_name="Water_Utility_Report.pdf",
        mime="application/pdf"
    )