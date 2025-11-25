import streamlit as st
import pandas as pd
import plotly.express as px
from components.container import card_container
import plotly.graph_objects as go

@st.cache_data
def load_data():
    df_billing = pd.read_csv('data/billing.csv', low_memory=False)
    df_billing = df_billing[df_billing['date'] != 'date'].reset_index(drop=True)
    df_billing['date'] = pd.to_datetime(df_billing['date'], format='%Y-%m-%d')
    
    # Convert numeric columns from strings to numbers
    df_billing['consumption_m3'] = pd.to_numeric(df_billing['consumption_m3'], errors='coerce')
    df_billing['billed'] = pd.to_numeric(df_billing['billed'], errors='coerce')
    df_billing['paid'] = pd.to_numeric(df_billing['paid'], errors='coerce')
    
    # Normalize country names to title case
    if 'country' in df_billing.columns:
        df_billing['country'] = df_billing['country'].str.title()
    
    df_financial = pd.read_csv('data/all_fin_service.csv')
    df_financial['date_MMYY'] = pd.to_datetime(df_financial['date_MMYY'], format='%b/%y')
    
    return df_billing, df_financial



def show(selected_countries, year_range=None):
    st.title("Financial Performance")
    
    df_billing, df_financial = load_data()
    filtered_df = df_billing.copy()
    
    # Filter by selected countries from global filter
    if selected_countries:
        filtered_df = filtered_df[filtered_df['country'].isin(selected_countries)]
    
    # Filter by year range from global filter
    if year_range:
        start_year, end_year = year_range
        filtered_df = filtered_df[
            (filtered_df['date'].dt.year >= start_year) & 
            (filtered_df['date'].dt.year <= end_year)
        ]

    # Calculating some KPIs - some used, some not
    total_revenue = filtered_df['paid'].sum()
    total_billed = filtered_df['billed'].sum()
    collection_rate = (total_revenue / total_billed * 100) if total_billed > 0 else 0
    total_opex = df_financial['opex'].sum()
    cost_recovery_rate = (df_financial['sewer_revenue'].sum() / total_opex * 100) if total_opex > 0 else 0
    outstanding = total_billed - total_revenue
    total_customers = filtered_df['customer_id'].nunique()
    avg_revenue_per_customer = df_billing['paid'].sum() / df_billing['customer_id'].nunique()


    avg_consumption = filtered_df['consumption_m3'].mean()
    

    #KPIs to display: Total Revenue, Collection rate, Cost recovery rate
    #st.markdown("### Key Performance Indicators")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with card_container(key="kpi_metric1"):
            st.metric("Total Revenue", f"${total_revenue:,.0f}")
    
    with col2:
        with card_container(key="kpi_metric2"):
            st.metric("Collection Rate", f"{collection_rate:.2f}%")

    with col3:
        with card_container(key="kpi_metric3"):
            st.metric("Cost Recovery Rate", f"{cost_recovery_rate:.2f}%")
    
    #KPIS: outstanding, active customers, avg revenue/customer
    col1, col2, col3 = st.columns(3)

    with col1: 
        with card_container(key="kpi_metric4"): 
            st.metric("Outstanding", f"${outstanding:,.0f}")

    with col2: 
        with card_container(key="kpi_metric5"): 
            st.metric("Active Customers", f"{total_customers}")

    with col3: 
        with card_container(key="kpi_metric6"): 
            st.metric("Avg Revenue / Customer", f"${avg_revenue_per_customer:.2f}")

    st.markdown("---")

    # Preparing data by country
    monthly_by_country = filtered_df.groupby([pd.Grouper(key='date', freq='MS'), 'country'], dropna=False).agg({'paid': 'sum'}).reset_index()
    
    # Remove any rows where country is NaN
    monthly_by_country = monthly_by_country.dropna(subset=['country'])

    st.markdown("### Revenue Breakdown & Trends")

    tab1, tab2 = st.tabs(["Revenue Trend", "Tab2"])
        # Create line chart with plotly express
    with tab1:
        fig_revenue = px.line(
            monthly_by_country,
            x='date',
            y='paid',
            color='country',
            title='Yearly Revenue Trend by Country',
            labels={'date': 'Month', 'paid': 'Revenue ($)', 'country': 'Country'},
            markers=True
        )
        
        fig_revenue.update_layout(
            height=500,
            hovermode='x unified',
            plot_bgcolor='#212750',
            xaxis=dict(showgrid=True, gridcolor='lightgray'),
            yaxis=dict(showgrid=True, gridcolor='lightgray', tickprefix='$', tickformat=',.0f')
        )
        
        fig_revenue.update_traces(line=dict(width=3), marker=dict(size=8))
        
        st.plotly_chart(fig_revenue, use_container_width=True)

    def calculate_kpis_by_group(df, group_col):
        return (
            df.groupby(group_col)
            .agg(
                total_revenue=('paid', 'sum'),   
                total_billed=('billed', 'sum')  
            )
            .reset_index()
            .sort_values('total_revenue', ascending=False)
        )

    with tab2: 
        st.markdown("Hello")

    
    st.markdown("### Collection Efficiency & Payment Analysis")

    tab1, tab2 = st.tabs(["Tab1", "Tab2"])
    
    with tab1: 
        st.markdown("Hello")

    with tab2: 
        st.markdown("Hello")

    
    st.markdown("### Customer Segmentation & Behavior")

    tab1, tab2 = st.tabs(["Tab1", "Tab2"])
    
    with tab1: 
        st.markdown("Hello")

    with tab2: 
        st.markdown("Hello")
    
    
    st.markdown("### Sewer Service & Financial Performance")

    tab1, tab2 = st.tabs(["Tab1", "Tab2"])
    
    with tab1: 
        st.markdown("Hello")

    with tab2: 
        st.markdown("Hello")

    
    st.markdown("### Operational Cost Analysis")

    tab1, tab2 = st.tabs(["Tab1", "Tab2"])
    
    with tab1: 
        st.markdown("Hello")

    with tab2: 
        st.markdown("Hello")
    
    