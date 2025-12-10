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
from modules import service_delivery
from modules import overview #added from modules
from modules import profile
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

if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = None
    st.session_state["name"] = None
    st.session_state["username"] = None

# --- SEARCH UTILITY FUNCTIONS ---
@st.cache_data
def get_column_types(df):
    # Caches column type mapping for performance
    col_types = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            col_types[col] = 'numeric'
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            col_types[col] = 'datetime'
        else:
            col_types[col] = 'text'
    return col_types

def add_search_examples():
    # Displays search tips and examples
    st.subheader("💡 Tips for using the Search Functionality")
    st.info(f"""
    The Search Functionality allows you to quickly query across all loaded datasets ({len(st.session_state.data)} files) to locate specific records, values, or trends.
    """)

    st.markdown("##### 📚 Search Examples / User Stories")
    st.markdown("""
    1.  **Simple Keyword Search (Quick Find):**
        * Query: `2023-08` or `malawi`
        * Why: Quickly find all records across all files for a specific time period or country.
    2.  **Targeted Filter (Outlier/Target Finding):**
        * Mode: Targeted Filter, Dataset: `data/water_service`, Column: `w_supplied`, Operator: `Greater than or equal to (>=)`, Value: `1000000`
        * Why: Find all *water\_service* records where the reported volume of `w_supplied` (water supplied) exceeds 1 million cubic meters.
    """)


def show_data_index_search(data, search_mode, target_dataset, target_column, target_operator, comparison_value):
    # Main function to process and display search results
    st.title("🔎 Search Results")
    found_results = False

    def apply_filter(df, column, operator, value):
        # Applies filtering logic based on input
        final_mask = pd.Series([True] * len(df), index=df.index)
        col = df[column]
        
        # Handle numeric comparisons
        if operator in ['>= (Greater than or equal to)', '<= (Less than or equal to)', '== (Equal to)']:
            numeric_col = pd.to_numeric(col, errors='coerce')
            numeric_val = float(value)
            
            if operator.startswith('>='):
                final_mask = numeric_col >= numeric_val
            elif operator.startswith('<='):
                final_mask = numeric_col <= numeric_val
            elif operator.startswith('=='):
                final_mask = numeric_col == numeric_val
                
        # Handle text comparisons
        elif operator in ['contains', 'starts with', 'ends with']:
            text_col = col.astype(str).str.lower()
            text_val = str(value).lower()
            
            if operator == 'contains':
                final_mask = text_col.str.contains(text_val, na=False, regex=False)
            elif operator == 'starts with':
                final_mask = text_col.str.startswith(text_val, na=False)
            elif operator == 'ends with':
                final_mask = text_col.str.endswith(text_val, na=False)
                
        # Handle date comparisons
        elif operator == 'Date contains YYYY-MM-DD':
            # Safely convert date column to string format for searching
            date_str = col.dt.strftime('%Y-%m-%d').astype(str).str.lower()
            final_mask = date_str.str.contains(str(value).lower(), na=False, regex=False)
        
        return df[final_mask]

    # --- Simple Keyword Search logic ---
    if search_mode == 'Simple Keyword Search':
        search_term = comparison_value 
        st.subheader(f"Simple Search: Keyword **'{search_term}'** across all {len(data)} datasets")
        search_lower = search_term.lower() if search_term else None

        if not search_lower:
            st.info("Enter a keyword to run the simple search.")
            add_search_examples()
            return
        
        for df_name, df in data.items():
            if df.empty: continue
                
            # Identify searchable columns (text/date)
            searchable_cols = df.select_dtypes(include=['object', 'datetime64']).columns
            search_masks = []
            
            for col in searchable_cols:
                col_data = df[col]
                if pd.api.types.is_datetime64_any_dtype(col_data):
                    col_str = col_data.dt.strftime('%Y-%m-%d').astype(str).str.lower()
                else:
                    col_str = col_data.astype(str).str.lower()
                    
                search_masks.append(col_str.str.contains(search_lower, na=False, regex=False))
            
            if search_masks:
                basic_mask = pd.concat(search_masks, axis=1).any(axis=1)
                filtered_df = df[basic_mask]
            else:
                filtered_df = pd.DataFrame() # No searchable columns

            if not filtered_df.empty:
                found_results = True
                st.markdown(f"**Found {len(filtered_df)} matches in file:** `{df_name}`")
                st.dataframe(filtered_df, use_container_width=True)


    # --- Targeted Filter logic ---
    elif search_mode == 'Targeted Filter (One Dataset)':
        st.subheader(f"Targeted Filter: Dataset `{target_dataset}`")
        
        if not target_dataset or not target_column or not comparison_value:
            st.info("Select a Dataset, Column, and enter a Comparison Value to run the targeted filter.")
            add_search_examples()
            return

        st.markdown(f"**Filtering applied:** Column **'{target_column}'** **{target_operator}** **'{comparison_value}'**")
        st.markdown("---")
        
        df = data.get(target_dataset)
        if df is None or target_column not in df.columns or df.empty:
            st.warning(f"Dataset `{target_dataset}` is empty or column `{target_column}` not found.")
            add_search_examples()
            return

        try:
            filtered_df = apply_filter(df, target_column, target_operator, comparison_value)
            
            if not filtered_df.empty:
                found_results = True
                st.markdown(f"**Found {len(filtered_df)} matches in file:** `{target_dataset}`")
                st.dataframe(filtered_df, use_container_width=True)

        except ValueError:
            st.error(f"Error applying filter: Please ensure the value '{comparison_value}' is compatible with the selected numeric/text operator and column '{target_column}'.")
            
        except Exception as e:
            st.error(f"An unexpected error occurred during filtering: {e}")


    if not found_results:
        st.warning(f"No records matched your search criteria.")

    st.markdown("---")
    add_search_examples()
# --- END SEARCH UTILITY FUNCTIONS ---

def reset_search_view():
    # Resets the search results view flag
    st.session_state.show_index_search = False

if st.session_state["authentication_status"] is None:
    show_login_page(authenticator, config)
            
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
    st.session_state['data'] = data # Store data for global search use

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
                "Profile",
                "Admin Panel"  # Only show for admins
            ]
        else:
            page_options = [
                "Executive Overview", 
                "Financial Performance",
                "Service Delivery",
                "Operations & Production",
                "Access", 
                "Profile"
            ]

        page = st.radio(
            "Select a Page", 
            page_options,
            on_change=reset_search_view  # NEW: Reset search flag on page change
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

        # --- Global Data Search (Action-driven) ---
        st.markdown("---")
        st.subheader("Search 🔍")
        
        # 1. Search Mode Selection
        search_mode = st.radio(
            "Select Search Mode",
            options=['Simple Keyword Search', 'Targeted Filter (One Dataset)'],
            key="search_mode",
            help="Simple search checks all text and date fields across all files. Targeted filter allows precise filtering on one file/column."
        )
        
        # Init session state for filter values
        if 'comparison_value' not in st.session_state: st.session_state['comparison_value'] = ""
        if 'selected_column' not in st.session_state: st.session_state['selected_column'] = None
        if 'selected_dataset' not in st.session_state: st.session_state['selected_dataset'] = None
        if 'selected_operator' not in st.session_state: st.session_state['selected_operator'] = None

        
        # --- Simple Search Inputs ---
        if search_mode == 'Simple Keyword Search':
            st.text_input(
                "Enter Keyword/Value", 
                placeholder="e.g., 'Lesotho', '2023-08', '0.98'",
                key="comparison_value",
                help="Searches this value in all text/date fields across every dataset."
            )

        # --- Targeted Filter Inputs (Conditional) ---
        else:
            # Level 1: Dataset Selection
            dataset_options = [""] + sorted(data.keys())
            st.selectbox(
                "1. Select Dataset", 
                options=dataset_options,
                key="selected_dataset",
                index=0,
                help="Choose the specific data file you want to drill into."
            )
            
            # Determine column options and types based on selected dataset
            column_options = [""]
            col_types = {}
            if st.session_state.selected_dataset and st.session_state.selected_dataset in data:
                current_df = data[st.session_state.selected_dataset]
                column_options = [""] + sorted(current_df.columns.tolist())
                col_types = get_column_types(current_df)
                
            # Level 2: Column Selection
            st.selectbox(
                "2. Select Column", 
                options=column_options,
                key="selected_column",
                index=0,
                help="Choose the specific column you wish to filter."
            )

            # Level 3 & 4: Operator and Value (Conditional)
            if st.session_state.selected_column and st.session_state.selected_column in col_types:
                col_type = col_types[st.session_state.selected_column]
                
                # --- Operator Selection Logic ---
                if col_type == 'numeric':
                    operator_options = ['>= (Greater than or equal to)', '<= (Less than or equal to)', '== (Equal to)']
                    input_type = 'number'
                    input_placeholder = "e.g., 100000, 0.95"
                elif col_type == 'text':
                    operator_options = ['contains', 'starts with', 'ends with']
                    input_type = 'text'
                    input_placeholder = "e.g., Kenya, treatment"
                elif col_type == 'datetime':
                    operator_options = ['Date contains YYYY-MM-DD']
                    input_type = 'text'
                    input_placeholder = "e.g., 2023-08"
                else:
                    operator_options = []
                    input_type = 'text'
                    input_placeholder = ""

                st.selectbox(
                    "3. Select Operator", 
                    options=operator_options,
                    key="selected_operator",
                    help=f"Operators specific to {col_type} data."
                )
                
                # --- Comparison Value Input (Type-aware) ---
                if input_type == 'number':
                    st.number_input(
                        "4. Enter Comparison Value", 
                        placeholder=input_placeholder,
                        key="comparison_value",
                        step=0.01,
                        help="Enter the numeric value for comparison."
                    )
                else:
                    st.text_input(
                        "4. Enter Comparison Value", 
                        placeholder=input_placeholder,
                        key="comparison_value",
                        help="Enter the text or date value for comparison."
                    )
                
            else:
                # Clear operator/value if column is unselected
                st.session_state.selected_operator = None
                st.session_state.comparison_value = ""


        # Init session state for search flag
        if 'show_index_search' not in st.session_state:
            st.session_state['show_index_search'] = False

        # Callback to trigger search and set flag
        def trigger_search():
            if st.session_state.search_mode == 'Simple Keyword Search' and st.session_state.comparison_value:
                st.session_state.show_index_search = True
            elif st.session_state.search_mode == 'Targeted Filter (One Dataset)' and st.session_state.selected_dataset and st.session_state.selected_column and st.session_state.comparison_value:
                st.session_state.show_index_search = True
            else:
                # Reset search if criteria are insufficient
                st.session_state.show_index_search = False

                
        # Button to execute search
        st.button(
            "Search", 
            on_click=trigger_search, 
            type="primary",
            use_container_width=True
        )
        
        # Logic to clear search results if inputs are cleared
        if st.session_state.search_mode == 'Simple Keyword Search' and not st.session_state.comparison_value:
            st.session_state.show_index_search = False
        elif st.session_state.search_mode == 'Targeted Filter (One Dataset)' and (not st.session_state.selected_dataset or not st.session_state.selected_column or not st.session_state.comparison_value):
            st.session_state.show_index_search = False

        st.markdown("---")
        # ---------------------------------------------

    # --- MAIN PAGE EXECUTION LOGIC ---

    # 1. OVERRIDE: Show search results if triggered
    if st.session_state.show_index_search:
        show_data_index_search(
            data, 
            st.session_state.search_mode,
            st.session_state.selected_dataset,
            st.session_state.selected_column,
            st.session_state.selected_operator,
            st.session_state.comparison_value
        )
        
    # 2. STANDARD: Show dashboard page if no search active
    else: 
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
            service_delivery.show(selected_countries, year_range)

        elif page == "Operations & Production":
            #st.write("Production goes here...")
            production_operations_page()

        elif page == "Access":
            access.render_access_page(selected_countries, year_range)

        elif page == "Profile": 
            profile.show()
            
        elif page == "Admin Panel":
            from modules import admin_panel
            admin_panel.show(config)

    # PDF_PATH = "assets/report.pdf"

    # with st.sidebar:
    #     st.markdown("---")
    #     try:
    #         if os.path.exists(PDF_PATH):
    #             with open(PDF_PATH, "rb") as pdf_file:
    #                 st.download_button(
    #                     label="📄 Download Report PDF",
    #                     data=pdf_file,
    #                     file_name="Water_Utility_Report.pdf",
    #                     mime="application/pdf",
    #                 )
    #         else:
    #             st.warning("📄 Report PDF not available")
    #     except Exception as e:
    #         st.warning("📄 Report PDF not available")

            
    # def dummy_function():
    #     st.write("Testing just for now")

    # with st.sidebar:
    #     st.button(
    #         label="🤖 Chat with an AI Bot",
    #         on_click=dummy_function, 
    #         type="primary"
    #     )
    
    with st.sidebar: 
        st.markdown("---")
        if st.session_state.get('authentication_status'):  
            authenticator.logout("Logout", "sidebar")
 
