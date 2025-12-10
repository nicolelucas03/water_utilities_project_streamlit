import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from components.container import card_container

@st.cache_data
def load_financial_data():
    """Load financial performance data"""
    try:
        df_billing = pd.read_csv('data/billing.csv', low_memory=False)
        df_billing = df_billing[df_billing['date'] != 'date'].reset_index(drop=True)
        df_billing['date'] = pd.to_datetime(df_billing['date'], format='%Y-%m-%d')
        
        # Convert numeric columns
        df_billing['consumption_m3'] = pd.to_numeric(df_billing['consumption_m3'], errors='coerce')
        df_billing['billed'] = pd.to_numeric(df_billing['billed'], errors='coerce')
        df_billing['paid'] = pd.to_numeric(df_billing['paid'], errors='coerce')
        
        if 'country' in df_billing.columns:
            df_billing['country'] = df_billing['country'].str.title()
        
        df_financial = pd.read_csv('data/all_fin_service.csv')
        df_financial['date_MMYY'] = pd.to_datetime(df_financial['date_MMYY'], format='%b/%y')
        
        if 'country' in df_financial.columns:
            df_financial['country'] = df_financial['country'].str.title()
        
        return df_billing, df_financial
    except Exception as e:
        st.error(f"Error loading financial data: {e}")
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data
def load_service_delivery_data():
    """Load service delivery data"""
    try:
        df_water = pd.read_csv('data/water_service.csv', low_memory=False)
        df_water = df_water[df_water['date_MMYY'] != 'date_MMYY'].reset_index(drop=True)
        df_water['date'] = pd.to_datetime(df_water['date_MMYY'], format='%b/%y', errors='coerce')
        
        # Convert numeric columns
        numeric_cols_water = [
            'households', 'tests_chlorine', 'tests_ecoli', 'tests_conducted_chlorine', 
            'test_conducted_ecoli', 'test_passed_chlorine', 'tests_passed_ecoli',
            'w_supplied', 'total_consumption', 'metered', 'ww_capacity'
        ]
        for col in numeric_cols_water:
            if col in df_water.columns:
                df_water[col] = pd.to_numeric(df_water[col], errors='coerce')
        
        if 'country' in df_water.columns:
            df_water['country'] = df_water['country'].astype(str).str.title()
        
        df_sanitation = pd.read_csv('data/s_service.csv', low_memory=False)
        df_sanitation = df_sanitation[df_sanitation['date_MMYY'] != 'date_MMYY'].reset_index(drop=True)
        df_sanitation['date'] = pd.to_datetime(df_sanitation['date_MMYY'], format='%b/%y', errors='coerce')
        
        numeric_cols_sanitation = [
            'households', 'sewer_connections', 'public_toilets', 'workforce', 
            'f_workforce', 'ww_collected', 'ww_treated', 'ww_reused', 
            'w_supplied', 'hh_emptied', 'fs_treated', 'fs_reused'
        ]
        for col in numeric_cols_sanitation:
            if col in df_sanitation.columns:
                df_sanitation[col] = pd.to_numeric(df_sanitation[col], errors='coerce')
        
        if 'country' in df_sanitation.columns:
            df_sanitation['country'] = df_sanitation['country'].astype(str).str.title()
        
        df_water = df_water.dropna(subset=['date'])
        df_sanitation = df_sanitation.dropna(subset=['date'])
        
        return df_water, df_sanitation
    except Exception as e:
        st.error(f"Error loading service delivery data: {e}")
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data
def load_access_data():
    """Load access data"""
    try:
        water = pd.read_csv("data/water_access.csv")
        san = pd.read_csv("data/s_access.csv")
        
        for df in (water, san):
            if "country" in df.columns:
                df["country"] = df["country"].astype(str).str.title()
            df["date_YY"] = pd.to_datetime(df["date_YY"], format="%Y")
            df["year"] = df["date_YY"].dt.year
        
        return water, san
    except Exception as e:
        st.error(f"Error loading access data: {e}")
        return pd.DataFrame(), pd.DataFrame()
        

def show(selected_countries, year_range=None):
    """
    Executive Overview page - main dashboard landing page
    
    Parameters:
    - selected_countries: list of selected countries from global filter
    - year_range: tuple of (start_year, end_year) from global filter
    """
    
    # Header Section
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Executive Overview")
    with col2:
        st.markdown(
            f"<div style='text-align: right; padding-top: 20px;'>Welcome, <strong>{st.session_state['name']}</strong></div>", 
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    # Load all data
    df_billing, df_financial = load_financial_data()
    df_water, df_sanitation = load_service_delivery_data()
    water_access, san_access = load_access_data()
    
    # Check if data loaded successfully
    if df_billing.empty and df_water.empty and water_access.empty:
        st.error("Unable to load dashboard data. Please check data files.")
        return
    
    # Apply global filters
    def apply_filters(df, date_col='date'):
        """Apply country and year filters to dataframe"""
        filtered = df.copy()
        
        if selected_countries and 'country' in filtered.columns:
            filtered = filtered[filtered['country'].isin(selected_countries)]
        
        if year_range and date_col in filtered.columns:
            start_year, end_year = year_range
            filtered = filtered[
                (filtered[date_col].dt.year >= start_year) & 
                (filtered[date_col].dt.year <= end_year)
            ]
        
        return filtered
    
    # Apply filters to all datasets
    df_billing = apply_filters(df_billing, 'date')
    df_financial = apply_filters(df_financial, 'date_MMYY')
    df_water = apply_filters(df_water, 'date')
    df_sanitation = apply_filters(df_sanitation, 'date')
    
    # For access data, handle differently due to year column
    if year_range and not water_access.empty:
        start_year, end_year = year_range
        water_access = water_access[(water_access['year'] >= start_year) & (water_access['year'] <= end_year)]
        san_access = san_access[(san_access['year'] >= start_year) & (san_access['year'] <= end_year)]
    
    if selected_countries:
        if not water_access.empty:
            water_access = water_access[water_access['country'].isin(selected_countries)]
            san_access = san_access[san_access['country'].isin(selected_countries)]
    
    #FINANCIAL PERFORMANCE KPIS
    
    st.markdown("## Financial Performance")
    
    # Calculate Financial KPIs
    total_revenue = df_billing['paid'].sum() if not df_billing.empty else 0
    total_billed = df_billing['billed'].sum() if not df_billing.empty else 0
    collection_rate = (total_revenue / total_billed * 100) if total_billed > 0 else 0
    
    total_sewer_revenue = df_financial['sewer_revenue'].sum() if len(df_financial) > 0 else 0
    total_opex = df_financial['opex'].sum() if len(df_financial) > 0 else 0
    cost_recovery_rate = (total_sewer_revenue / total_opex * 100) if total_opex > 0 else 0
    
    outstanding = total_billed - total_revenue
    
    # Display Financial KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with card_container(key="exec_total_revenue"):
            st.metric("Total Revenue", f"${total_revenue:,.0f}", help="Total water revenue collected")
    
    with col2:
        delta_color = "normal" if collection_rate >= 85 else "inverse"
        with card_container(key="exec_collection_rate"):
            st.metric(
                "Collection Rate", 
                f"{collection_rate:.1f}%",
                delta=f"Target: 85%",
                delta_color=delta_color,
                help="Percentage of billed amounts actually paid (Target: 85%)"
            )
    
    with col3:
        delta_color = "normal" if cost_recovery_rate >= 100 else "inverse"
        with card_container(key="exec_cost_recovery"):
            st.metric(
                "Cost Recovery Rate", 
                f"{cost_recovery_rate:.1f}%",
                delta=f"Target: 100%",
                delta_color=delta_color,
                help="Sewer revenue vs operating expenses (Target: 100%)"
            )
    
    with col4:
        with card_container(key="exec_outstanding"):
            st.metric("Outstanding Balance", f"${outstanding:,.0f}", help="Uncollected receivables")
    
    st.markdown("---")
    
    #SERVICE DELIVERY
    
    st.markdown("## Service Delivery & Quality")
    
    # Calculate Service Delivery KPIs
    total_supplied = df_water['w_supplied'].sum() if not df_water.empty else 0
    total_consumed = df_water['total_consumption'].sum() if not df_water.empty else 0
    nrw_volume = total_supplied - total_consumed
    nrw_percent = (nrw_volume / total_supplied) * 100 if total_supplied > 0 else 0
    
    tests_total_conducted = (
        df_water['tests_conducted_chlorine'].sum() + df_water['test_conducted_ecoli'].sum()
    ) if not df_water.empty else 0
    tests_total_passed = (
        df_water['test_passed_chlorine'].sum() + df_water['tests_passed_ecoli'].sum()
    ) if not df_water.empty else 0
    overall_pass_rate = (tests_total_passed / tests_total_conducted) * 100 if tests_total_conducted > 0 else 0
    
    total_ww_collected = df_sanitation['ww_collected'].sum() if not df_sanitation.empty else 0
    ww_treatment_rate = (
        df_sanitation['ww_treated'].sum() / total_ww_collected * 100
    ) if total_ww_collected > 0 else 0
    
    latest_households = df_sanitation['households'].max() if not df_sanitation.empty else 0
    total_sewer_connections = df_sanitation['sewer_connections'].max() if not df_sanitation.empty else 0
    sewer_coverage = (total_sewer_connections / latest_households) * 100 if latest_households > 0 else 0
    
    # Display Service Delivery KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # NRW - lower is better
        delta_color = "inverse" if nrw_percent < 25 else "normal"
        with card_container(key="exec_nrw"):
            st.metric(
                "Non-Revenue Water", 
                f"{nrw_percent:.1f}%",
                delta=f"Target: <25%",
                delta_color=delta_color,
                help="Water supplied but not billed (Target: <25%)"
            )
    
    with col2:
        delta_color = "normal" if overall_pass_rate >= 98 else "inverse"
        with card_container(key="exec_water_quality"):
            st.metric(
                "Water Quality Pass Rate", 
                f"{overall_pass_rate:.1f}%",
                delta=f"Target: 98%+",
                delta_color=delta_color,
                help="Average of Chlorine and E.coli tests passed (Target: 98%+)"
            )
    
    with col3:
        delta_color = "normal" if ww_treatment_rate >= 80 else "inverse"
        with card_container(key="exec_ww_treatment"):
            st.metric(
                "Wastewater Treatment", 
                f"{ww_treatment_rate:.1f}%",
                delta=f"Target: >80%",
                delta_color=delta_color,
                help="Percentage of collected wastewater that is treated (Target: >80%)"
            )
    
    with col4:
        with card_container(key="exec_sewer_coverage"):
            st.metric(
                "Sewer Coverage", 
                f"{sewer_coverage:.1f}%",
                help="Sewer connections / Households"
            )
    
    st.markdown("---")
    
    #ACCESS
    
    st.markdown("## Access")
    
    def pop_weighted_pct(df, pct_col):
        """Population-weighted average of a percentage column"""
        if df.empty or 'popn_total' not in df.columns:
            return 0.0
        total_pop = df['popn_total'].sum()
        if total_pop == 0:
            return 0.0
        return float((df[pct_col] * df['popn_total']).sum() / total_pop)
    
    water_safe_pct = pop_weighted_pct(water_access, 'safely_managed_pct')
    san_safe_pct = pop_weighted_pct(san_access, 'safely_managed_pct')
    
    no_basic_water_pct = (
        pop_weighted_pct(water_access, 'limited_pct') +
        pop_weighted_pct(water_access, 'unimproved_pct') +
        pop_weighted_pct(water_access, 'surface_water_pct')
    )
    
    open_def_pct = pop_weighted_pct(san_access, 'open_def_pct')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with card_container(key="exec_safe_water"):
            st.metric(
                "Safely Managed Water", 
                f"{water_safe_pct:.1f}%",
                help="Population with safely managed water services"
            )
    
    with col2:
        with card_container(key="exec_safe_san"):
            st.metric(
                "Safely Managed Sanitation", 
                f"{san_safe_pct:.1f}%",
                help="Population with safely managed sanitation services"
            )
    
    with col3:
        delta_color = "inverse" if no_basic_water_pct < 10 else "normal"
        with card_container(key="exec_no_basic_water"):
            st.metric(
                "No Basic Water", 
                f"{no_basic_water_pct:.1f}%",
                delta=f"Target: <10%",
                delta_color=delta_color,
                help="Population without basic water access (Target: <10%)"
            )
    
    with col4:
        delta_color = "inverse" if open_def_pct < 5 else "normal"
        with card_container(key="exec_open_def"):
            st.metric(
                "Open Defecation", 
                f"{open_def_pct:.1f}%",
                delta=f"Target: <5%",
                delta_color=delta_color,
                help="Population practicing open defecation (Target: <5%)"
            )
    
    st.markdown("---")
    
    #KEY TRENDS
    st.markdown("## Key Trends")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Revenue Trend
        if not df_billing.empty:
            monthly_revenue = df_billing.groupby(
                pd.Grouper(key='date', freq='MS')
            )['paid'].sum().reset_index()
            
            fig_revenue = px.line(
                monthly_revenue,
                x='date',
                y='paid',
                title='Monthly Revenue Trend',
                labels={'date': 'Month', 'paid': 'Revenue ($)'}
            )
            
            fig_revenue.update_layout(
                height=300,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f8f8f2'),
                xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)', tickprefix='$', tickformat=',.0f')
            )
            
            fig_revenue.update_traces(line=dict(color='#5681d0', width=3))
            
            st.plotly_chart(fig_revenue, use_container_width=True)
    
    with col2:
        # NRW Trend
        if not df_water.empty:
            df_supply_grouped = df_water.groupby(
                pd.Grouper(key='date', freq='MS')
            )[['w_supplied', 'total_consumption']].sum().reset_index()
            
            df_supply_grouped['NRW_Percent'] = (
                (df_supply_grouped['w_supplied'] - df_supply_grouped['total_consumption']) / 
                df_supply_grouped['w_supplied'] * 100
            )
            
            fig_nrw = px.line(
                df_supply_grouped,
                x='date',
                y='NRW_Percent',
                title='Non-Revenue Water Trend',
                labels={'date': 'Month', 'NRW_Percent': 'NRW (%)'}
            )
            
            fig_nrw.add_hline(
                y=25, 
                line_dash="dash", 
                line_color="rgba(255,107,107,0.5)",
                annotation_text="Target: 25%"
            )
            
            fig_nrw.update_layout(
                height=300,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f8f8f2'),
                xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
            )
            
            fig_nrw.update_traces(line=dict(color='#FFD700', width=3))
            
            st.plotly_chart(fig_nrw, use_container_width=True)
    
    st.markdown("---")
    
    #ALERTS
    
    st.markdown("## ⚠️ Priority Alerts")
    
    alerts = []
    
    # Financial alerts
    if collection_rate < 85:
        alerts.append({
            'severity': 'high',
            'category': 'Financial',
            'message': f"Collection rate ({collection_rate:.1f}%) is below target (85%)",
            'action': 'Review payment enforcement and customer engagement strategies'
        })
    
    if cost_recovery_rate < 100:
        alerts.append({
            'severity': 'medium',
            'category': 'Financial',
            'message': f"Cost recovery rate ({cost_recovery_rate:.1f}%) is below break-even (100%)",
            'action': 'Analyze operational costs and revenue optimization opportunities'
        })
    
    # Service delivery alerts
    if nrw_percent > 40:
        alerts.append({
            'severity': 'high',
            'category': 'Operations',
            'message': f"NRW rate ({nrw_percent:.1f}%) is critically high (>40%)",
            'action': 'Urgent: Investigate leaks, theft, and metering accuracy'
        })
    elif nrw_percent > 25:
        alerts.append({
            'severity': 'medium',
            'category': 'Operations',
            'message': f"NRW rate ({nrw_percent:.1f}%) exceeds target (25%)",
            'action': 'Implement leak detection and network maintenance program'
        })
    
    if overall_pass_rate < 98:
        alerts.append({
            'severity': 'high',
            'category': 'Quality',
            'message': f"Water quality pass rate ({overall_pass_rate:.1f}%) is below standard (98%)",
            'action': 'Critical: Review disinfection processes and water treatment protocols'
        })
    
    if ww_treatment_rate < 80:
        alerts.append({
            'severity': 'medium',
            'category': 'Environment',
            'message': f"Wastewater treatment rate ({ww_treatment_rate:.1f}%) is below target (80%)",
            'action': 'Assess treatment plant capacity and operational efficiency'
        })
    
    # Access alerts
    if no_basic_water_pct > 10:
        alerts.append({
            'severity': 'high',
            'category': 'Access',
            'message': f"{no_basic_water_pct:.1f}% of population lacks basic water access",
            'action': 'Prioritize infrastructure expansion in underserved areas'
        })
    
    if open_def_pct > 5:
        alerts.append({
            'severity': 'high',
            'category': 'Sanitation',
            'message': f"{open_def_pct:.1f}% of population practices open defecation",
            'action': 'Urgent: Expand sanitation facilities and public awareness programs'
        })
    
    # Display alerts
    if alerts:
        # Sort by severity
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        alerts.sort(key=lambda x: severity_order[x['severity']])
        
        for alert in alerts:
            severity_color = '#ff6b6b' if alert['severity'] == 'high' else '#ffd93d'
            severity_icon = '🔴' if alert['severity'] == 'high' else '🟡'
            
            st.markdown(f"""
            <div style="padding: 15px; border-left: 5px solid {severity_color}; 
                        background-color: rgba(255, 255, 255, 0.05); margin-bottom: 15px;">
                <p style="font-size: 14px; color: #f8f8f2; margin: 0;">
                    {severity_icon} <strong>[{alert['category']}]</strong> {alert['message']}<br>
                    <em style="font-size: 12px; color: #aaa;">→ Recommended Action: {alert['action']}</em>
                </p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ All key performance indicators are within acceptable ranges")
    
