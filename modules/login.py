import streamlit as st

def show_login_page(authenticator, config):
    st.markdown("""
        <style>
        /* Hide sidebar and main menu on login page */
        [data-testid="stSidebar"] {display: none;}
        
        /* Center the content */
        .main > div {
            padding-top: 2rem;
        }
        
        /* Login container styling */
        .login-container {
            max-width: 450px;
            margin: 0 auto;
            padding: 2rem;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        /* Logo container */
        .logo-container {
            text-align: center;
            margin-bottom: 2rem;
        }
        
        /* Header styling */
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .login-header h1 {
            color: #1e3a8a;
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        
        .login-header p {
            color: #64748b;
            font-size: 0.95rem;
        }
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
            background-color: transparent;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 0;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 0;
            padding: 12px 28px;
            font-weight: 500;
            background-color: transparent;
            border-bottom: 3px solid transparent;
            transition: all 0.3s ease;
            color: #64748b;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            color: #2563eb;
            background-color: rgba(37, 99, 235, 0.05);
        }
        
        .stTabs [aria-selected="true"] {
            background-color: transparent;
            color: #2563eb;
            border-bottom: 3px solid #2563eb;
            font-weight: 600;
        }
        
        /* Button styling */
        .stButton > button {
            width: 100%;
            background-color: #2563eb;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.75rem;
            font-weight: 500;
            font-size: 1rem;
            transition: background-color 0.3s;
        }
        
        .stButton > button:hover {
            background-color: #1d4ed8;
        }
        
        /* Input field styling */
        .stTextInput > div > div > input {
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            padding: 0.75rem;
        }
        
        /* Footer */
        .login-footer {
            text-align: center;
            margin-top: 2rem;
            padding-top: 2rem;
            border-top: 1px solid #e2e8f0;
            color: #64748b;
            font-size: 0.85rem;
        }
        
        /* Info box styling */
        .stAlert {
            border-radius: 8px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div class="login-header">
                <h1>Water Utilities Dashboard</h1>
                <p>Welcome! Sign in to access performance metrics and analytics</p>
            </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔐 Sign In", "📝 Register"])
        
        with tab1:
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.session_state.get("authentication_status") is False:
                st.error("⚠️ Incorrect username or password. Please try again.")
            
            try:
                authenticator.login(max_login_attempts=6)
            except Exception as e:
                st.error(f"Login error: {str(e)}")
            
            st.markdown("<br>", unsafe_allow_html=True)
   
            with st.expander("🔒 Need help signing in?"):
                st.markdown("""
                    - Ensure your username and password are correct
                    - Passwords are case-sensitive
                    - Contact your administrator if you've forgotten your credentials
                    - Maximum 6 login attempts before temporary lockout
                """)
        
        with tab2:
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.info("👋 Create a new account to access the dashboard")
            
            try:
                (email_of_registered_user,
                 username_of_registered_user,
                 name_of_registered_user) = authenticator.register_user()
                
                if email_of_registered_user:
                    config['credentials']['usernames'][username_of_registered_user]['role'] = 'country'
                    config['credentials']['usernames'][username_of_registered_user]['country'] = None
                    
                    st.success('✅ Account created successfully!')
          
                    with open('config.yaml', 'w') as file:
                        yaml.dump(config, file, default_flow_style=False)
                    
                    st.info('👉 Please switch to the **Sign In** tab to access your account')
                    st.balloons()
                    
            except Exception as e:
                st.error(f"Registration error: {str(e)}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            with st.expander("ℹ️ Registration Information"):
                st.markdown("""
                    - All new accounts start with 'country' role access
                    - An administrator will assign your specific country access
                    - Use a valid email address for account recovery
                    - Choose a strong password with mixed characters
                """)
        
        st.markdown("""
            <div class="login-footer">
                <p>Water Services Regulatory Board (WASREB)</p>
                <p>© 2025 All rights reserved</p>
            </div>
        """, unsafe_allow_html=True)

