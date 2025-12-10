import streamlit as st
import yaml
from yaml.loader import SafeLoader
from components.container import card_container

def show():
    #ACCOUNT SETTINGS
    st.title("Manage Profile")
    
    authenticator = st.session_state.get("authenticator")
    config = st.session_state.get("config")
    
    if not authenticator or not config:
        st.error("Authentication system not found. Please log in again.")
        return

    tab1, tab2, tab3 = st.tabs(["Profile", "Reset Password", "Update Profile"])
    
    with tab1:
        st.markdown("#### **Your Profile Information**")

        with card_container(key="profile_card"):   
            col1, col2 = st.columns([1, 3])     
            with col1:
                st.markdown("**Username**")
                st.markdown("**Full Name**")
                st.markdown("**Email**")
                st.markdown("**Role**")
            with col2:
                st.markdown(f"{st.session_state.get('username', 'N/A')}")
                st.markdown(f"{st.session_state.get('name', 'N/A')}")
                st.markdown(
                    f"{config['credentials']['usernames'].get(st.session_state['username'], {}).get('email', 'N/A')}")
                st.markdown(f"{st.session_state.get('user_role', 'N/A').title()}")
                ##st.caption(f"Role: {user_role.title()}")
    with tab2:
        
        try:
            if authenticator.reset_password(st.session_state["username"], location='main'):
                st.success('Password updated successfully!')
                
                with open('config.yaml', 'w') as file:
                    yaml.dump(config, file, default_flow_style=False)              
        except Exception as e:
            st.error(f"❌ {e}")
    
    with tab3:
        
        try:
            if authenticator.update_user_details(st.session_state["username"], location='main'):
                st.success('Username updated successfully!')
                
                with open('config.yaml', 'w') as file:
                    yaml.dump(config, file, default_flow_style=False)
                    
        except Exception as e:
            st.error(f"❌ {e}")
