import streamlit as st
import pandas as pd
import plotly.express as px

@st.cache_data
def load_data():
    df = pd.read_csv('data/billing.csv')
    df['date_MMYY'] = pd.to_datetime(df['date_MMYY'], format='%b/%y')
    return df

def show():
    st.title("Financial Performance")
    
    df = load_data()

    st.sidebar.header("Filters")

    if 'country' in df.columns:
        selected_country = st.sidebar.multiselect(
            "Select Country",
            options=df['country'].unique(),
            default=df['country'].unique()
        )
        filtered_df = df[df['country'].isin(selected_country)]
    else:
        filtered_df = df

    total_revenue = filtered_df['paid'].sum()
    total_billed = filtered_df['billed'].sum()
    collection_rate = (total_revenue / total_billed * 100) if total_billed > 0 else 0
    avg_consumption = filtered_df['consumption_m3'].mean()
    total_customers = filtered_df['customer_id'].nunique()
    outstanding = total_billed - total_revenue

    st.subheader("Key Performance Indicators")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Revenue", f"${total_revenue:,.0f}")

    with col2:
        st.metric("Collection Rate", f"{collection_rate:.1f}%")

    with col3:
        st.metric("Avg Consumption", f"{avg_consumption:.1f} m³")

    with col4:
        st.metric("Outstanding", f"${outstanding:,.0f}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Revenue Trend")
        monthly_revenue = filtered_df.groupby('date_MMYY')['paid'].sum().reset_index()
        monthly_revenue = monthly_revenue.sort_values('date_MMYY')
        fig = px.line(monthly_revenue, x='date_MMYY', y='paid', 
                      labels={'paid': 'Revenue ($)', 'date_MMYY': 'Date'},
                      title='Monthly Revenue')
        st.plotly_chart(fig, use_container_width=True)
