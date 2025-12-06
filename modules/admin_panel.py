import streamlit as st
import yaml
from yaml.loader import SafeLoader
import pandas as pd
from components.container import card_container

def show(config):
    st.markdown("""
        <style>
        
        /* User card styling */
        .user-card {
            background: #1a1a3d;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            border-left: 4px solid #5681d0;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .user-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(86, 129, 208, 0.4);
        }
        
        .user-header {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid rgba(86, 129, 208, 0.3);
        }
        
        .user-avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: linear-gradient(135deg, #5681d0 0%, #4a6bb8 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #f8f8f2;
            font-weight: 600;
            font-size: 1.2rem;
            margin-right: 1rem;
            box-shadow: 0 2px 8px rgba(86, 129, 208, 0.4);
        }
        
        .user-info h4 {
            margin: 0;
            color: #f8f8f2;
            font-size: 1.1rem;
        }
        
        .user-info p {
            margin: 0.25rem 0 0 0;
            color: #f8f8f2;
            font-size: 0.85rem;
            opacity: 0.7;
        }
        
        /* Role badge */
        .role-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .role-admin {
            background: rgba(255, 193, 7, 0.2);
            color: #ffc107;
            border: 1px solid #ffc107;
        }
        
        .role-country {
            background: rgba(86, 129, 208, 0.2);
            color: #5681d0;
            border: 1px solid #5681d0;
        }
        
        /* Section headers */
        .section-header {
            display: flex;
            align-items: center;
            margin: 2rem 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid rgba(86, 129, 208, 0.3);
        }
        
        .section-header h2 {
            color: #f8f8f2;
            font-size: 1.5rem;
            margin: 0;
        }
        
        /* Button improvements */
        .stButton > button {
            border-radius: 8px;
            padding: 0.5rem 1.5rem;
            font-weight: 500;
            transition: all 0.3s;
            background-color: #5681d0;
            color: #f8f8f2;
            border: none;
        }
        
        .stButton > button:hover {
            background-color: #4a6bb8;
            box-shadow: 0 4px 12px rgba(86, 129, 208, 0.4);
        }
        
        /* Select box improvements */
        .stSelectbox > div > div {
            border-radius: 8px;
            background-color: #1a1a3d;
            border-color: rgba(86, 129, 208, 0.3);
        }
        
        /* Radio button styling */
        .stRadio > div {
            background-color: #1a1a3d;
            padding: 0.5rem 1rem;
            border-radius: 8px;
        }
        
        /* Info box styling */
        .stInfo {
            background-color: rgba(86, 129, 208, 0.1);
            border-left-color: #5681d0;
        }
        
        /* Success box styling */
        .stSuccess {
            background-color: rgba(76, 175, 80, 0.1);
        }
        </style>
    """, unsafe_allow_html=True)
    
    username = st.session_state.get("username")
    user_role = config['credentials']['usernames'].get(username, {}).get('role', 'country')
    
    if user_role != 'admin':
        st.markdown("""
            <div style="text-align: center; padding: 4rem 2rem;">
                <h1 style="color: #ff6b6b; font-size: 4rem; margin: 0;">⛔</h1>
                <h2 style="color: #f8f8f2; margin: 1rem 0;">Access Denied</h2>
                <p style="color: rgba(248, 248, 242, 0.7);">Admin privileges are required to access this page.</p>
            </div>
        """, unsafe_allow_html=True)
        return
    
    st.markdown("""
        <div class="admin-header">
            <h1>Admin Panel</h1>
            <p>Manage users, roles, and system permissions</p>
        </div>
    """, unsafe_allow_html=True)
    
    
    users = config['credentials']['usernames']
    total_users = len(users)
    admin_count = sum(1 for u in users.values() if u.get('role') == 'admin')
    country_users = sum(1 for u in users.values() if u.get('role') == 'country')
    assigned_users = sum(1 for u in users.values() if u.get('country') is not None)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with card_container(key="total-users"): 
            st.metric("Total Users", f"{total_users}")

    with col2:
        with card_container(key="admin-count"):
            st.metric("Administrators", f"{admin_count}")
    
    with col3:
        with card_container(key="country-users"): 
            st.metric("Country Users", f"{country_users}")
    
    with col4:
        with card_container(key="assigned-countries"): 
            st.metric("Assigned Countries", f"{assigned_users}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # View Toggle as Tabs
    tab1, tab2 = st.tabs(["📋 Card View", "📊 Table View"])
    
    with tab1:
        # Card View - More visual with collapsible edit section
        for uname, udata in users.items():
            name = udata.get('name', uname)
            email = udata.get('email', 'N/A')
            current_role = udata.get('role', 'country')
            current_country = udata.get('country', None)
            
            # Create initials for avatar
            initials = ''.join([n[0].upper() for n in name.split()[:2]])
            
            with st.expander(f"👤 **{name}** (@{uname})", expanded=False):
                # User info section
                col_avatar, col_info = st.columns([1, 5])
                
                with col_avatar:
                    st.markdown(f"""
                        <div class="user-avatar" style="margin: 0;">
                            {initials}
                        </div>
                    """, unsafe_allow_html=True)
                
                with col_info:
                    st.markdown(f"""
                        <div style="padding-left: 1rem;">
                            <p style="color: #f8f8f2; margin: 0; font-size: 0.9rem;">📧 {email}</p>
                            <p style="color: rgba(248, 248, 242, 0.7); margin: 0.25rem 0 0 0; font-size: 0.85rem;">
                                Current Role: <span class="role-badge role-{current_role}">{current_role.upper()}</span>
                            </p>
                            {f'<p style="color: rgba(248, 248, 242, 0.7); margin: 0.25rem 0 0 0; font-size: 0.85rem;">🌍 Country: <strong>{current_country}</strong></p>' if current_country else '<p style="color: rgba(248, 248, 242, 0.5); margin: 0.25rem 0 0 0; font-size: 0.85rem;">🌍 Country: Not Assigned</p>'}
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("---")
                st.markdown("Edit User Settings")
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    new_role = st.selectbox(
                        "Role",
                        options=['admin', 'country'],
                        index=0 if current_role == 'admin' else 1,
                        key=f"role_{uname}",
                        help="Admins have full access, country users are restricted to their assigned country"
                    )
                
                with col2:
                    if new_role == 'country':
                        available_countries = ['Cameroon', 'Lesotho', 'Malawi', 'Uganda']
                        
                        # Better handling of current country index
                        if current_country in available_countries:
                            default_index = available_countries.index(current_country) + 1
                        else:
                            default_index = 0
                        
                        new_country = st.selectbox(
                            "Assigned Country",
                            options=[None] + available_countries,
                            index=default_index,
                            key=f"country_{uname}",
                            help="Select which country data this user can access"
                        )
                    else:
                        new_country = None
                        st.info("🌍 Access to all countries")
                
                with col3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Update", key=f"update_{uname}", use_container_width=True, type="primary"):
                        config['credentials']['usernames'][uname]['role'] = new_role
                        config['credentials']['usernames'][uname]['country'] = new_country
                        
                        with open('config.yaml', 'w') as file:
                            yaml.dump(config, file, default_flow_style=False)
                        
                        st.success(f"✅ Updated {name}'s settings")
                        st.rerun()
    
    with tab2:
        # Table View - More compact
        user_data = []
        for uname, udata in users.items():
            user_data.append({
                'Username': uname,
                'Name': udata.get('name', uname),
                'Email': udata.get('email', 'N/A'),
                'Role': udata.get('role', 'country'),
                'Country': udata.get('country', 'Not Assigned')
            })
        
        df = pd.DataFrame(user_data)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Role": st.column_config.SelectboxColumn(
                    "Role",
                    options=["admin", "country"],
                ),
            }
        )
        
        st.info("💡 Switch to Card View for detailed user management")
    