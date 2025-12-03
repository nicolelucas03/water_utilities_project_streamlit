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

    st.markdown("---")
    #ACCOUNT SETTINGS
    st.markdown("### Manage Account")
    
    authenticator = st.session_state.get("authenticator")
    config = st.session_state.get("config")
    
    if not authenticator or not config:
        st.error("Authentication system not found. Please log in again.")
        return

    tab1, tab2, tab3 = st.tabs(["Profile", "Security", "Username"])
    
    with tab1:
        st.markdown("#### **Your Profile Information**")

        with card_container(key="profile_card"):   
            col1, col2 = st.columns([1, 3])     
            with col1:
                st.markdown("**Username**")
                st.markdown("**Full Name**")
                st.markdown("**Email**")
            with col2:
                st.markdown(f"{st.session_state.get('username', 'N/A')}")
                st.markdown(f"{st.session_state.get('name', 'N/A')}")
                st.markdown(
                    f"{config['credentials']['usernames'].get(st.session_state['username'], {}).get('email', 'N/A')}")
        
    with tab2:
        st.markdown("For security, enter your current password before setting a new one")
        st.markdown("")
        
        try:
            if authenticator.reset_password(st.session_state["username"], location='main'):
                st.success('Password updated successfully!')
                
                with open('config.yaml', 'w') as file:
                    yaml.dump(config, file, default_flow_style=False)              
        except Exception as e:
            st.error(f"❌ {e}")
    
    with tab3:
        st.markdown("Choose a new username for your account")
        st.markdown("") 
        
        try:
            if authenticator.update_user_details(st.session_state["username"], location='main'):
                st.success('Username updated successfully!')
                
                with open('config.yaml', 'w') as file:
                    yaml.dump(config, file, default_flow_style=False)
                    
        except Exception as e:
            st.error(f"❌ {e}")