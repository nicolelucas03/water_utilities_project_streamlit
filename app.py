import streamlit as st
st.set_page_config(
    page_title = "Water Utilities Dashboard",
    layout = "wide",
    initial_sidebar_state = "expanded"
)

import pandas as pd 
import plotly.express as px 
import plotly.graph_objects as go
from plotly.subplots import make_subplots 
import numpy as np
from modules import financial_performance
import os
from components.container import card_container
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities import LoginError
import yaml
from yaml.loader import SafeLoader

#st.logo("assets/wasreb_logo_dashboard.jpg", size="large", link= "https://wasreb.go.ke/", icon_image="assets/wasreb_logo_dashboard.jpg")

# Load Poppins globally and apply dark theme
# Load Poppins globally and apply dark theme
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">

<style>
body, .stApp, .st-emotion-cache, [data-testid] * {
    font-family: 'Poppins', sans-serif !important;
    color: #f8f8f2 !important;
}

html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: #212750 !important;
}

/* Hide Streamlit header and toolbar */
header[data-testid="stHeader"] {
    background-color: #212750 !important;
    height: 0px !important;
    min-height: 0px !important;
}

/* Hide the hamburger menu */
#MainMenu {
    visibility: hidden !important;
}

/* Hide "Made with Streamlit" footer */
footer {
    visibility: hidden !important;
}

/* Remove top padding caused by hidden header */
.main .block-container {
    padding-top: 2rem !important;
}

main > div {
    padding-top: 3rem !important;
}

[data-testid="stSidebar"] {
    background-color: #1a1a3d !important;
    padding-top: 2rem !important;
}

[data-testid="stSidebar"] * {
    color: #f8f8f2 !important;
}

h1, h2, h3, h4, h5, h6 {
    color: #f8f8f2 !important;
}

[data-testid="metric-container"] {
    background-color: #1a1a3d !important;
    border: 1px solid #5681d0 !important;
    border-radius: 12px !important;
    padding: 18px !important;
}

[data-testid="stWidgetLabel"] {
    visibility: hidden !important;
    height: 0 !important;
    overflow: hidden !important;
}

[data-testid="stPlotlyChart"] * {
    color: #f8f8f2 !important;
}

/* Fix toolbar icons color when visible */
.stApp [data-testid="stToolbar"] {
    background-color: #212750 !important;
}
            
 /* Style buttons to match dark theme */
.stButton > button {
    background-color: #5681d0 !important;
    color: #f8f8f2 !important;
    border: 1px solid #5681d0 !important;
    border-radius: 8px !important;
    padding: 0.5rem 1rem !important;
    font-weight: 500 !important;
    width: 100% !important;
}

.stButton > button:hover {
    background-color: #6a92e0 !important;
    border-color: #6a92e0 !important;
    color: #ffffff !important;
}

.stButton > button:active {
    background-color: #4a71c0 !important;
}

/* Style download button specifically */
.stDownloadButton > button {
    background-color: #5681d0 !important;
    color: #f8f8f2 !important;
    border: 1px solid #5681d0 !important;
    border-radius: 8px !important;
    padding: 0.5rem 1rem !important;
    font-weight: 500 !important;
    width: 100% !important;
}

.stDownloadButton > button:hover {
    background-color: #6a92e0 !important;
    border-color: #6a92e0 !important;
    color: #ffffff !important;
}

[data-testid="collapsedControl"] {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
</style>
""", unsafe_allow_html=True)

#User Authentication
# Load credentials from the YAML file
with open("config.yaml") as file:
     config = yaml.load(file, Loader=SafeLoader)

# Pre-hashing all plain text passwords once
# stauth.Hasher.hash_passwords(config['credentials'])

# Initialize the authenticator
authenticator = stauth.Authenticate(
     config["credentials"],
     config["cookie"]["name"],
     config["cookie"]["key"],
     config["cookie"]["expiry_days"],)

# Store the authenticator object in the session state
st.session_state["authenticator"] = authenticator
# Store the config in the session state so it can be updated later
st.session_state["config"] = config

try:
    authenticator.login(location="main", key="login-demo-app-home")
except LoginError as e:
    st.error(e)

#Conditional logic that will show content based on auth status
if st.session_state["authentication_status"]:
    # with st.sidebar: 
        # st.write(f'Welcome, **{st.session_state["name"]}**')
    

    
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
        st.image("assets/wasreb_logo_dashboard.jpg", width=60)
        st.write(f'Welcome, **{st.session_state["name"]}**')
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
    PDF_PATH = "assets/report.pdf"

    with st.sidebar:
        try:
            if os.path.exists(PDF_PATH):
                with open(PDF_PATH, "rb") as pdf_file:
                    st.download_button(
                        label="📄 Download Report PDF",
                        data=pdf_file,
                        file_name="Water_Utility_Report.pdf",
                        mime="application/pdf",
                    )
            else:
                st.warning("📄 Report PDF not available")
        except Exception as e:
            st.warning("📄 Report PDF not available")

            
    #For an AI chatbot
    def dummy_function():
        st.write("Testing just for now")

    with st.sidebar:
        st.button(
            label="🤖 Chat with an AI Bot",
            on_click=dummy_function 
        )
    authenticator.logout('Logout', 'sidebar')

elif st.session_state["authentication_status"] is False: 
    st.error('Username/password is incorrect')

elif st.session_state["authentication_status"] is None: 
    st.info('Log in to access the dashboard')