import streamlit as st
import pandas as pd
import plotly.express as px
from components.container import card_container

@st.cache_data
def load_data():
    df = pd.read_csv('data/billing.csv', low_memory=False)
    df = df[df['date'] != 'date'].reset_index(drop=True)
    df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
    
    # Convert numeric columns from strings to numbers
    df['consumption_m3'] = pd.to_numeric(df['consumption_m3'], errors='coerce')
    df['billed'] = pd.to_numeric(df['billed'], errors='coerce')
    df['paid'] = pd.to_numeric(df['paid'], errors='coerce')
    
    # Normalize country names to title case
    if 'country' in df.columns:
        df['country'] = df['country'].str.title()
    
    return df


def show(selected_countries, year_range=None):
    st.title("Financial Performance")
    
    df = load_data()

    # Apply global filters from app.py
    filtered_df = df.copy()
    
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

    # Calculating some KPIs
    total_revenue = filtered_df['paid'].sum()
    total_billed = filtered_df['billed'].sum()
    collection_rate = (total_revenue / total_billed * 100) if total_billed > 0 else 0
    avg_consumption = filtered_df['consumption_m3'].mean()
    total_customers = filtered_df['customer_id'].nunique()
    outstanding = total_billed - total_revenue

    # Placing the KPIs on dashboard
    st.markdown("### Key Performance Indicators")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with card_container(key="kpi_metric1"):
            st.metric("Total Revenue", f"${total_revenue:,.0f}")
    
    with col2:
        with card_container(key="kpi_metric2"):
            st.metric("Total Billed", f"${total_billed:,.0f}")
    
    with col3:
        with card_container(key="kpi_metric3"):
            st.metric("Collection Rate", f"{collection_rate:.1f}%")
    
    with col4:
        with card_container(key="kpi_metric4"): 
            st.metric("Outstanding Amount", f"${outstanding:,.0f}")

    st.markdown("---")

    # Preparing data by country
    monthly_by_country = filtered_df.groupby([pd.Grouper(key='date', freq='MS'), 'country'], dropna=False).agg({'paid': 'sum'}).reset_index()
    
    # Remove any rows where country is NaN
    monthly_by_country = monthly_by_country.dropna(subset=['country'])


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
    
