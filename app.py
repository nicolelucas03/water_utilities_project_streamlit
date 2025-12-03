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
import os
import streamlit_authenticator as stauth
import yaml

from modules import financial_performance
from modules import overview
from components.container import card_container
from streamlit_authenticator.utilities import LoginError
from yaml.loader import SafeLoader

api_key = st.secrets["API_KEY_LOGIN"]
st.logo("assets/wasreb_logo_dashboard.jpg", size="large", link= "https://wasreb.go.ke/", icon_image="assets/wasreb_logo_dashboard.jpg")

def load_css(file_path):
    with open(file_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

load_css("styles/dashboard.css")

#USER AUTHENTICATION: HMM, MAYBE CHANGE UI? 
with open("config.yaml") as file:
     config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
     config["credentials"],
     config["cookie"]["name"],
     config["cookie"]["key"],
     config["cookie"]["expiry_days"],)

st.session_state["authenticator"] = authenticator
st.session_state["config"] = config
if st.session_state.get("authentication_status") is None:
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        try: 
            authenticator.login(max_login_attempts=6) 
        except Exception as e: 
            st.error(e)
    
    with tab2:
        try:
            (email_of_registered_user,
             username_of_registered_user,
             name_of_registered_user) = authenticator.register_user(
             )
            
            if email_of_registered_user:
                st.success('User registered successfully')
                with open('config.yaml', 'w') as file:
                    yaml.dump(config, file, default_flow_style=False)
                st.info('Please switch to the Login tab and sign in')
        except Exception as e:
            st.error(e)

elif st.session_state["authentication_status"] is False:
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.error('Username/password is incorrect')
        try: 
            authenticator.login(max_login_attempts=6) 
        except Exception as e: 
            st.error(e)
    
    with tab2:
        try:
            (email_of_registered_user,
             username_of_registered_user,
             name_of_registered_user) = authenticator.register_user(
                 pre_authorization=False
             )
            
            if email_of_registered_user:
                st.success('User registered successfully')
                with open('config.yaml', 'w') as file:
                    yaml.dump(config, file, default_flow_style=False)
                st.info('Please switch to the Login tab and sign in')
        except Exception as e:
            st.error(e)
            
elif st.session_state["authentication_status"]:
    
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

        all_fin_service['date_MMYY'] = pd.to_datetime(all_fin_service['date_MMYY'], format='%b/%y')
        all_national['date_YY'] = pd.to_datetime(all_national['date_YY'], format='%Y')
        billing['date'] = pd.to_datetime(billing['date'], format='%Y-%m-%d')
        production['date_YYMMDD'] = pd.to_datetime(production['date_YYMMDD'], format='%Y/%m/%d')
        s_access['date_YY'] = pd.to_datetime(s_access['date_YY'], format='%Y')
        s_service['date_MMYY'] = pd.to_datetime(s_service['date_MMYY'], format='%b/%y')
        w_access['date_YY'] = pd.to_datetime(w_access['date_YY'], format='%Y')
        w_service['date_MMYY'] = pd.to_datetime(w_service['date_MMYY'], format='%b/%y')

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


    with st.sidebar:
        # st.image("assets/wasreb_logo_dashboard.jpg", width=60)
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


    if page == "Executive Overview":
        overview.show()

    elif page == "Financial Performance":
        financial_performance.show(selected_countries, year_range)

    elif page == "Service Delivery":
        st.write("Service data goes here...")

    elif page == "Operations & Production":
        st.write("Production goes here...")

    elif page == "Access":
        st.write("Access data goes here...")

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

            
    def dummy_function():
        st.write("Testing just for now")

    with st.sidebar:
        st.button(
            label="🤖 Chat with an AI Bot",
            on_click=dummy_function, 
            type="primary"
        )
    
    with st.sidebar: 
        st.markdown("---")
        if st.session_state.get('authentication_status'):  
            authenticator.logout("Logout", "sidebar")
            
