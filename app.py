import streamlit as st
import pandas as pd 
import plotly.express as px 
import plotly.graph_objects as go 
from plotly.subplots import make_subplots 
import numpy as np
from modules import financial_performance


st.set_page_config(
    page_title = "Water Utilities Dashboard",
    layout = "wide",
    initial_sidebar_state = "expanded"
)

# Loading Poppins font from Google Fonts and applyng globally. Folder didn't work for me.
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --app-font: 'Poppins', sans-serif; }
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"], .stApp, .block-container {
            font-family: var(--app-font) !important;
        }
        /* Ensure common text elements use Poppins */
        h1, h2, h3, h4, h5, h6, p, span, label, button, input {
            font-family: var(--app-font) !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

#CSS will go here - for future use
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
    
    # Removing duplicate header rows that may exist in the data
    billing = billing[billing['date'] != 'date'].reset_index(drop=True)

    # Parsing all dates
    all_fin_service['date_MMYY'] = pd.to_datetime(all_fin_service['date_MMYY'], format='%b/%y')
    all_national['date_YY'] = pd.to_datetime(all_national['date_YY'], format='%Y')
    billing['date'] = pd.to_datetime(billing['date'], format='%Y-%m-%d')
    production['date_YYMMDD'] = pd.to_datetime(production['date_YYMMDD'], format='%Y/%m/%d')
    s_access['date_YY'] = pd.to_datetime(s_access['date_YY'], format='%Y')
    s_service['date_MMYY'] = pd.to_datetime(s_service['date_MMYY'], format='%b/%y')
    w_access['date_YY'] = pd.to_datetime(w_access['date_YY'], format='%Y')
    w_service['date_MMYY'] = pd.to_datetime(w_service['date_MMYY'], format='%b/%y')

# Fixing the uppercase/lowercase country names
    dfs_to_normalize = [all_fin_service, all_national, billing, production, s_access, s_service, w_access, w_service]
    for df in dfs_to_normalize:
        if 'country' in df.columns:
            df['country'] = df['country'].str.title()

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
    #TO DO: Troubleshoot with st.logo again!!
    #logo in sidebar with css because st.logo does not work for me
    #TO DO: Link site to logo maybe?
    st.image("assets/wasreb_logo_dashboard.jpg", width=60)
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
        default=None,
    )

    all_years = []
    for df_name, df in data.items(): 
        if "date_YY" in df.columns: 
            all_years.extend(df["date_YY"].dt.year.unique())
        elif "date_MMYY" in df.columns: 
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

#This is for keeping the pages as radio buttons. Might change to pages?? 
if page == "Executive Overview":
    st.write("KPIs will go here...")

elif page == "Financial Performance":
    financial_performance.show(selected_countries, year_range)

elif page == "Service Delivery":
    st.write("Service data goes here...")

elif page == "Operations & Production":
    st.write("Production goes here...")

elif page == "Access":
    st.write("Access data goes here...")

#For a report (just a test right now): 
with st.sidebar:
    st.download_button(
        label= "📄 Download Report PDF",
        data=open("assets/report.pdf", "rb").read(),
        file_name="Water_Utility_Report.pdf",
        mime="application/pdf",

    )

#For an AI chatbot
def dummy_function():
    st.write("Testing just for now")

with st.sidebar:
    st.button(
        label="🤖 Chat with an AI Bot",
        on_click=dummy_function 
    )

