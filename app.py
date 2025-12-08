import streamlit as st
import pandas as pd 
import plotly.express as px 
import plotly.graph_objects as go 
from plotly.subplots import make_subplots 
import numpy as np
from modules import financial_performance
import os
import streamlit_authenticator as stauth
import yaml
from modules import financial_performance
from modules.operations_production import production_operations_page
from modules import access
from modules import overview #added from modules
from modules.login import show_login_page
from components.container import card_container
from streamlit_authenticator.utilities import LoginError
from yaml.loader import SafeLoader
from modules.chatbot import bot, DATASETS   


st.set_page_config(
    page_title = "Water Utilities Dashboard",
    layout = "wide",
    initial_sidebar_state = "expanded"
)


#api_key = st.secrets["API_KEY_LOGIN"] #TEMPORARY COMMENT (avoids issues with streamlit run) 
st.logo("assets/wasreb_logo_dashboard.jpg", size="large", link= "https://wasreb.go.ke/", icon_image="assets/wasreb_logo_dashboard.jpg")

def load_css(file_path):
    with open(file_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

load_css("styles/dashboard.css")

#USER AUTHENTICATION: HMM, MAYBE CHANGE UI? 
# with open("config.yaml") as file:
#      config = yaml.load(file, Loader=SafeLoader)

# authenticator = stauth.Authenticate(
#      config["credentials"],
#      config["cookie"]["name"],
#      config["cookie"]["key"],
#      config["cookie"]["expiry_days"],)

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

# Defensive checks so we don't get a weird TypeError
if not isinstance(config, dict):
    st.error(f"config.yaml did not load as a dictionary. Got: {type(config)} with value: {config}")
    st.stop()

if "credentials" not in config or "cookie" not in config:
    st.error(f"config.yaml is missing 'credentials' or 'cookie' keys. Got keys: {list(config.keys())}")
    st.stop()

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

st.session_state["authenticator"] = authenticator
st.session_state["config"] = config
if st.session_state.get("authentication_status") is None:
    show_login_page(authenticator,config)
            
elif st.session_state["authentication_status"]:
    #GETTING USER'S ROLE AND ASSIGNED COUNTRY!- TESTING
    username = st.session_state["username"]
    user_data = config['credentials']['usernames'].get(username, {})
    user_role = user_data.get('role', 'country')  # Default to 'country' if not specified
    user_country = user_data.get('country', None)
    
    # Store in session state for easy access
    st.session_state['user_role'] = user_role
    st.session_state['user_country'] = user_country

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

        if user_role == 'country' and user_country:
            st.caption(f"Country: {user_country}")
        
        # st.markdown("---")

        if user_role == 'admin':
            page_options = [
                "Executive Overview", 
                "Financial Performance",
                "Service Delivery",
                "Operations & Production",
                "Access",
                "Admin Panel"  # Only show for admins
            ]
        else:
            page_options = [
                "Executive Overview", 
                "Financial Performance",
                "Service Delivery",
                "Operations & Production",
                "Access"
            ]

        page = st.radio(
            "Select a Page", 
            page_options
        )
        
        st.markdown("---")
        st.subheader("Global Filters")

        all_countries = set() 
        for df in data.values(): 
            if "country" in df.columns: 
                all_countries.update(df["country"].unique())

        if user_role == 'admin':
            selected_countries = st.multiselect( 
                "Select Countries", 
                options=sorted(all_countries),
                default=None,
                help="As an admin, you can view data from all countries"
            )
        elif user_role == 'country':
            if user_country:
                st.info(f"Viewing data for: **{user_country}**")
                selected_countries = [user_country]
            else:
                st.warning("No country assigned. Please contact admin.")
                selected_countries = []
        else:
            selected_countries = []

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

        # 🔽 ADD CHATBOT HERE
        st.markdown("---")
        st.markdown("## AI Water Data Assistant")

        st.info(
            """
            **Welcome to the AI Water Data Assistant!**

            Ask natural-language questions about the loaded water utility datasets.
            The assistant uses semantic search + planning + computation to 
            answer using real data. Ask simple, specific questions!

            Try asking:
            - *Does cameroon or malawi on average have a larger percentage of people under the safely managed water category?*
            - *What percentage of Cameroonians had safely managed water in 2020 compared to 2022?*
            """
        )

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        st.markdown("### Ask a Question")
        user_query = st.text_input("Type your question:")

        if st.button("Ask the Bot"):
            if user_query.strip():
                answer = bot.answer(user_query)
                st.session_state.chat_history.append(("You", user_query))
                st.session_state.chat_history.append(("Bot", answer))

        st.markdown("### Chat History")
        # Display newest messages at the top
        for speaker, msg in reversed(st.session_state.chat_history):
            if speaker == "You":
                st.markdown(f"**🧑 You:** {msg}")
            else:
                st.markdown(f"**🤖 Bot:** {msg}")
                
            st.markdown("<hr style='margin:5px 0;'>", unsafe_allow_html=True)



    elif page == "Financial Performance":
        financial_performance.show(selected_countries, year_range)

    elif page == "Service Delivery":
        st.write("Service data goes here...")

    elif page == "Operations & Production":
        #st.write("Production goes here...")
        production_operations_page()

    elif page == "Access":
        access.render_access_page(selected_countries, year_range)

    elif page == "Admin Panel":
        from modules import admin_panel
        admin_panel.show(config)

    PDF_PATH = "assets/report.pdf"

    with st.sidebar:
        st.markdown("---")
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
 
