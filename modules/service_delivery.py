import streamlit as st
import pandas as pd
import plotly.express as px
from components.container import card_container
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# --- Explainer Function for Consistency ---
def add_chart_explainer(title, description):
    """Adds a consistent description and disclaimer block below a chart."""
    # Retained: Changed border color from red to a subtle cyan/teal and added margin-bottom for spacing
    st.markdown(f"""
    <div style="padding: 10px; border-left: 5px solid #95e1d3; background-color: rgba(255, 255, 255, 0.05); margin-top: 15px; margin-bottom: 20px;">
        <p style="font-size: 14px; color: #f8f8f2;">
            <strong>Chart Commentary: {title}</strong><br>
            {description}
            <br>
            <em style="font-size: 11px; color: #aaa;">Disclaimer: This commentary is automatically generated and should be checked for accuracy.</em>
        </p>
    </div>
    """, unsafe_allow_html=True)


# --- Configuration and Data Loading ---

@st.cache_data
def load_data():
    """
    Loads, cleans, and transforms the water and sanitation service data.
    Assumes files are in the 'data/' directory relative to the app.
    """
    try:
        # Load Water Service Data
        df_water = pd.read_csv('data/water_service.csv', low_memory=False)
        
        # Clean up date column and convert to datetime
        df_water = df_water[df_water['date_MMYY'] != 'date_MMYY'].reset_index(drop=True)
        df_water['date'] = pd.to_datetime(df_water['date_MMYY'], format='%b/%y', errors='coerce')
        
        # Identify and convert numeric columns
        numeric_cols_water = [
            'households', 'tests_chlorine', 'tests_ecoli', 'tests_conducted_chlorine', 
            'test_conducted_ecoli', 'test_passed_chlorine', 'tests_passed_ecoli',
            'w_supplied', 'total_consumption', 'metered', 'ww_capacity'
        ]
        for col in numeric_cols_water:
            if col in df_water.columns:
                df_water[col] = pd.to_numeric(df_water[col], errors='coerce')
        
        # Normalize country names
        if 'country' in df_water.columns:
            df_water['country'] = df_water['country'].astype(str).str.title()
        
        # Load Sanitation Service Data
        df_sanitation = pd.read_csv('data/s_service.csv', low_memory=False)
        
        # Clean up date column and convert to datetime
        df_sanitation = df_sanitation[df_sanitation['date_MMYY'] != 'date_MMYY'].reset_index(drop=True)
        df_sanitation['date'] = pd.to_datetime(df_sanitation['date_MMYY'], format='%b/%y', errors='coerce')
        
        # Identify and convert numeric columns
        numeric_cols_sanitation = [
            'households', 'sewer_connections', 'public_toilets', 'workforce', 
            'f_workforce', 'ww_collected', 'ww_treated', 'ww_reused', 
            'w_supplied', 'hh_emptied', 'fs_treated', 'fs_reused'
        ]
        for col in numeric_cols_sanitation:
            if col in df_sanitation.columns:
                df_sanitation[col] = pd.to_numeric(df_sanitation[col], errors='coerce')
            
        # Normalize country names
        if 'country' in df_sanitation.columns:
            df_sanitation['country'] = df_sanitation['country'].astype(str).str.title()
        
        # Drop rows with invalid dates after conversion
        df_water = df_water.dropna(subset=['date'])
        df_sanitation = df_sanitation.dropna(subset=['date'])

        return df_water, df_sanitation

    except FileNotFoundError as e:
        st.error(f"Error loading data. Please ensure 'data/water_service.csv' and 'data/s_service.csv' are present. Detail: {e}")
        return pd.DataFrame(), pd.DataFrame()


def show(selected_countries, year_range=None):
    """
    Main function to run the Service Delivery Dashboard, accepting global filters.
    """
    st.title("Service Delivery")
    
    df_water, df_sanitation = load_data()

    if df_water.empty or df_sanitation.empty:
        return

    # --- Apply Global Filters ---
    
    filtered_water = df_water.copy()
    filtered_sanitation = df_sanitation.copy()

    if selected_countries:
        filtered_water = filtered_water[filtered_water['country'].isin(selected_countries)]
        filtered_sanitation = filtered_sanitation[filtered_sanitation['country'].isin(selected_countries)]
    
    if year_range:
        start_year, end_year = year_range
        filtered_water = filtered_water[
            (filtered_water['date'].dt.year >= start_year) & 
            (filtered_water['date'].dt.year <= end_year)
        ]
        filtered_sanitation = filtered_sanitation[
            (filtered_sanitation['date'].dt.year >= start_year) & 
            (filtered_sanitation['date'].dt.year <= end_year)
        ]

    if filtered_water.empty and filtered_sanitation.empty:
        st.warning("No data available for the selected filters.")
        return

    # --- Key Performance Indicators (KPIs) Section ---

    st.markdown("### Key Performance Indicators")
    
    # KPI Calculations
    total_supplied = filtered_water['w_supplied'].sum()
    total_consumed = filtered_water['total_consumption'].sum()
    nrw_volume = total_supplied - total_consumed
    nrw_percent = (nrw_volume / total_supplied) * 100 if total_supplied > 0 else 0
    
    tests_total_conducted = filtered_water['tests_conducted_chlorine'].sum() + filtered_water['test_conducted_ecoli'].sum()
    tests_total_passed = filtered_water['test_passed_chlorine'].sum() + filtered_water['tests_passed_ecoli'].sum()
    overall_pass_rate = (tests_total_passed / tests_total_conducted) * 100 if tests_total_conducted > 0 else 0

    latest_households = filtered_sanitation['households'].max()
    total_sewer_connections = filtered_sanitation['sewer_connections'].max()
    sewer_coverage = (total_sewer_connections / latest_households) * 100 if latest_households > 0 else 0
    
    total_ww_collected = filtered_sanitation['ww_collected'].sum()
    ww_treatment_rate = (filtered_sanitation['ww_treated'].sum() / total_ww_collected) * 100 if total_ww_collected > 0 else 0
    
    # --- REVISED Public Toilet Access KPI (Replacing FS) ---
    total_public_toilets = filtered_sanitation['public_toilets'].max()
    toilet_access_rate = (total_public_toilets / latest_households) * 1000 if latest_households > 0 else 0
    # Apply user requested formatting: 0.37 -> 37% by multiplying by 100
    toilet_access_percent = toilet_access_rate * 100 
    
    # --- REVISED Workforce KPI (Percentage Ratio display) ---
    total_workforce = filtered_sanitation['workforce'].sum()
    total_f_workforce = filtered_sanitation['f_workforce'].sum()
    
    if total_workforce > 0:
        f_percent = (total_f_workforce / total_workforce) * 100
        m_percent = 100 - f_percent # Re-calculate male %
        # New display format: F% : M%
        ratio_percent_display = f"{f_percent:.1f}% : {m_percent:.1f}%"
        help_text_workforce = "The percentage split of the workforce (Female % : Male %)."
    else:
        ratio_percent_display = "N/A"
        help_text_workforce = "No workforce data available."


    # KPIs Display
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with card_container(key="kpi_nrw"):
            st.metric("Non-Revenue Water (NRW) %", f"{nrw_percent:.1f}%", help="Water Supplied - Consumption. Values over 40% are generally considered high losses. Negative values indicate reported consumption exceeds supplied volume, suggesting data errors or unmetered supply sources.")
    
    with col2:
        with card_container(key="kpi_pass_rate"):
            st.metric("Overall Water Quality Pass Rate", f"{overall_pass_rate:.1f}%", help="Average of Chlorine and E.coli tests passed. Global best practice aims for 98% or higher.")

    with col3:
        with card_container(key="kpi_sewer_coverage"):
            st.metric("Sewer Connection Coverage", f"{sewer_coverage:.1f}%", help="Sewer Connections / Households (Latest). Essential for urban sanitation.")

    col4, col5, col6 = st.columns(3)
    
    with col4: 
        with card_container(key="kpi_ww_treat"): 
            st.metric("Wastewater Treatment Rate", f"{ww_treatment_rate:.1f}%", help="WW Treated / WW Collected. A key environmental performance indicator.")

    with col5: 
        with card_container(key="kpi_public_toilets"): 
            # Display as percentage, multiplied by 100
            st.metric("Public Toilet Access Rate (%)", f"{toilet_access_percent:.0f}%", help="This metric shows 100 times the rate of toilets per 1,000 households. If the rate is 0.37 per 1,000 HH, this is displayed as 37%.")

    with col6: 
        with card_container(key="kpi_f_workforce"): 
            st.metric("Workforce Gender Split (F : M)", ratio_percent_display, help=help_text_workforce)

    st.markdown("---")


    # --- SECTION 1: Water Network Efficiency (Now with two tabs) ---
    
    st.markdown("## 1. Water Network Efficiency 📉")
    
    tab_nrw_trend, tab_nrw_country = st.tabs(["Network Efficiency Trend", "NRW % by Country"]) 

    with tab_nrw_trend:
        # Monthly supply and NRW trend
        df_supply_grouped = filtered_water.groupby(
            pd.Grouper(key='date', freq='MS')
        )[['w_supplied', 'total_consumption']].sum().reset_index()
        
        df_supply_grouped['NRW_Volume'] = df_supply_grouped['w_supplied'] - df_supply_grouped['total_consumption']
        df_supply_grouped['NRW_Percent'] = (df_supply_grouped['NRW_Volume'] / df_supply_grouped['w_supplied']) * 100

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Color Change for high contrast
        fig.add_trace(
            go.Bar(x=df_supply_grouped['date'], y=df_supply_grouped['w_supplied'], name='Water Supplied', marker_color='#00FFFF', opacity=0.7), # Cyan
            secondary_y=False
        )
        fig.add_trace(
            go.Bar(x=df_supply_grouped['date'], y=df_supply_grouped['total_consumption'], name='Total Consumption', marker_color='#8A2BE2', opacity=0.7), # Purple
            secondary_y=False
        )
        
        fig.add_trace(
            go.Scatter(x=df_supply_grouped['date'], y=df_supply_grouped['NRW_Percent'], name='NRW %', 
                       mode='lines+markers', line=dict(color='#FFD700', width=3), marker=dict(size=6)), # Gold/Yellow
            secondary_y=True
        )

        fig.update_layout(
            title_text="Water Supplied, Consumed, and Non-Revenue Water (%) Over Time",
            barmode='overlay', height=450, hovermode='x unified', plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8f8f2'), 
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#f8f8f2'))
        )
        # NRW % Axis Fix: Ensure secondary_y label is correct
        fig.update_yaxes(title_text="Volume (m³)", secondary_y=False, color='#f8f8f2', tickformat=',.0f')
        fig.update_yaxes(title_text="NRW Percentage (%)", secondary_y=True, range=[min(0, df_supply_grouped['NRW_Percent'].min()), 100], color='#FFD700')
        st.plotly_chart(fig, use_container_width=True)
        
        # Explainer
        add_chart_explainer(
            "Water Supplied, Consumed, and Non-Revenue Water (%) Over Time", 
            "Displays the monthly trend for total water supplied (cyan bars) and total consumption (purple bars) on the left axis. The yellow line tracks the calculated Non-Revenue Water percentage on the right axis. Utilities generally target NRW below 25%, indicating that consistent high values suggest a need for urgent network repair and metering improvements."
        )

        # Summary Table
        st.markdown("**Monthly NRW Summary (Last 12 Months)**")
        df_nrw_summary = df_supply_grouped[['date', 'w_supplied', 'total_consumption', 'NRW_Percent']].copy()
        df_nrw_summary.columns = ['Date', 'Supplied (m³)', 'Consumed (m³)', 'NRW %']
        df_nrw_summary['Supplied (m³)'] = df_nrw_summary['Supplied (m³)'].apply(lambda x: f"{x:,.0f}")
        df_nrw_summary['Consumed (m³)'] = df_nrw_summary['Consumed (m³)'].apply(lambda x: f"{x:,.0f}")
        df_nrw_summary['NRW %'] = df_nrw_summary['NRW %'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(df_nrw_summary.sort_values(by='Date', ascending=False).head(12), hide_index=True, use_container_width=True)


    with tab_nrw_country:
        df_nrw_country = filtered_water.groupby('country').agg(
            w_supplied=('w_supplied', 'sum'),
            total_consumption=('total_consumption', 'sum')
        ).reset_index()
        
        # Robust filtering to prevent division by zero/negative consumption issues
        df_nrw_country = df_nrw_country[df_nrw_country['w_supplied'] > 0].copy()

        df_nrw_country['NRW_Percent'] = (
            (df_nrw_country['w_supplied'] - df_nrw_country['total_consumption']) / df_nrw_country['w_supplied'] * 100
        ).fillna(0).clip(-100, 100) # Clip to a reasonable range for plotting
        
        df_nrw_country = df_nrw_country.sort_values(by='NRW_Percent', ascending=False)

        if not df_nrw_country.empty:
            fig_nrw_country = px.bar(
                df_nrw_country,
                y='country', x='NRW_Percent', orientation='h',
                title='Non-Revenue Water (NRW) % by Country (Total Period)',
                labels={'NRW_Percent': 'NRW Percentage (%)', 'country': 'Country'},
                # Removed text='NRW_Percent'
                color='NRW_Percent', color_continuous_scale=px.colors.sequential.Reds_r
            )
            # CHANGE: texttemplate set to '' to completely remove text labels
            fig_nrw_country.update_traces(texttemplate='', textfont=dict(color='#f8f8f2')) 
            
            fig_nrw_country.update_layout(
                height=400, 
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)', 
                font=dict(color='#f8f8f2'), 
                showlegend=False,
                margin=dict(r=100) # Added margin to prevent y-axis labels from being cut off
            )
            st.plotly_chart(fig_nrw_country, use_container_width=True)
            
            # Explainer
            add_chart_explainer("Non-Revenue Water % by Country", "Shows the total Non-Revenue Water Percentage (Water Supplied - Consumption / Water Supplied) aggregated across the entire filtered period, broken down by country. Low percentages indicate efficient networks, but negative values can occur if recorded consumption exceeds supplied volume due to data logging or external supply/storage issues.")

            # Summary Table
            st.markdown("**NRW Summary by Country**")
            df_nrw_summary = df_nrw_country.copy()
            df_nrw_summary.columns = ['Country', 'Water Supplied (m³)', 'Total Consumption (m³)', 'NRW %']
            df_nrw_summary['Water Supplied (m³)'] = df_nrw_summary['Water Supplied (m³)'].apply(lambda x: f"{x:,.0f}")
            df_nrw_summary['Total Consumption (m³)'] = df_nrw_summary['Total Consumption (m³)'].apply(lambda x: f"{x:,.0f}")
            df_nrw_summary['NRW %'] = df_nrw_summary['NRW %'].apply(lambda x: f"{x:.1f}%")
            st.dataframe(df_nrw_summary, hide_index=True, use_container_width=True)

        else:
            st.info("No valid data available for NRW % breakdown (Water Supplied is zero or negative).")
            


    st.markdown("---")


    # --- SECTION 2: Water Quality Testing (Multiple Tabs) ---
    
    st.markdown("## 2. Water Quality Testing 🔬")

    tab_chlorine, tab_ecoli = st.tabs(["Chlorine Test Results", "E. Coli Pass Rate by Country"])
    
    # Water Quality Test Breakdown - Chart 2.1 (Chlorine Pie)
    with tab_chlorine:
        df_quality_sum = filtered_water[[
            'tests_conducted_chlorine', 'test_passed_chlorine',
            'test_conducted_ecoli', 'tests_passed_ecoli'
        ]].sum().to_frame().T.fillna(0)
        
        chlorine_data = {
            'Result': ['Passed', 'Failed'],
            'Count': [
                df_quality_sum['test_passed_chlorine'].iloc[0], 
                df_quality_sum['tests_conducted_chlorine'].iloc[0] - df_quality_sum['test_passed_chlorine'].iloc[0]
            ]
        }
        df_chlorine = pd.DataFrame(chlorine_data)
        
        if df_chlorine['Count'].sum() > 0:
            
            # --- REVERTED LAYOUT: Horizontal two-column layout ---
            col_chart, col_content = st.columns([1, 1])
            
            with col_chart:
                fig_chlorine = px.pie(
                    df_chlorine, values='Count', names='Result', title='Overall Chlorine Test Results',
                    color='Result', color_discrete_map={'Passed': '#6bcf7f', 'Failed': '#ff6b6b'}
                )
                fig_chlorine.update_traces(textinfo='percent+label', hole=.3, textfont=dict(color='#ffffff'))
                fig_chlorine.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8f8f2'), legend=dict(font=dict(color='#f8f8f2')))
                st.plotly_chart(fig_chlorine, use_container_width=True)

            with col_content:
                # Explainer placed first
                add_chart_explainer(
                    "Overall Chlorine Test Results", 
                    "A summary of all Chlorine tests conducted across all countries and periods. Chlorine is a critical indicator of water safety and residual disinfection. A failure rate higher than 5% should trigger an investigation into the disinfection process or potential contamination in the distribution network."
                )

                # Summary Table placed second
                st.markdown("### Chlorine Test Summary")
                df_chlorine_summary = df_chlorine.copy()
                df_chlorine_summary.columns = ['Result', 'Total Count']
                df_chlorine_summary['Total Count'] = df_chlorine_summary['Total Count'].apply(lambda x: f"{x:,.0f}")
                st.dataframe(df_chlorine_summary, hide_index=True, use_container_width=True)

        else:
            st.info("No Chlorine test data available for selected filters.")
            
        


    # E. Coli Test Bar Chart - Chart 2.2 (E.coli Bar)
    with tab_ecoli:
        df_ecoli_country = filtered_water.groupby('country').agg({
            'test_conducted_ecoli': 'sum',
            'tests_passed_ecoli': 'sum'
        }).reset_index()
        
        df_ecoli_country['Pass_Rate'] = (
            df_ecoli_country['tests_passed_ecoli'] / df_ecoli_country['test_conducted_ecoli'] * 100
        ).fillna(0) 

        df_ecoli_country = df_ecoli_country.sort_values(by='Pass_Rate', ascending=True)

        if not df_ecoli_country.empty:
            fig_ecoli_bar = px.bar(
                df_ecoli_country,
                y='country', x='Pass_Rate', orientation='h',
                title='E. Coli Pass Rate by Country',
                labels={'Pass_Rate': 'Pass Rate (%)', 'country': 'Country'},
                text='Pass_Rate', color_continuous_scale=['#ff6b6b', '#6bcf7f'], color='Pass_Rate'
            )
            fig_ecoli_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside', textfont=dict(color='#f8f8f2'))
            fig_ecoli_bar.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8f8f2'), showlegend=False)
            st.plotly_chart(fig_ecoli_bar, use_container_width=True)
            
            # Explainer
            add_chart_explainer("E. Coli Pass Rate by Country", "Compares the E. Coli water quality test pass rate across different countries, calculated as Tests Passed / Tests Conducted for E. Coli. E. Coli presence is a direct indicator of fecal contamination, making a 100% pass rate the absolute target for safe drinking water. Any value below 100% signifies a severe public health risk.")

            # Summary Table
            st.markdown("**E. Coli Pass Rate Summary**")
            df_ecoli_summary = df_ecoli_country[['country', 'test_conducted_ecoli', 'tests_passed_ecoli', 'Pass_Rate']].copy()
            df_ecoli_summary.columns = ['Country', 'Tests Conducted', 'Tests Passed', 'Pass Rate %']
            df_ecoli_summary['Tests Conducted'] = df_ecoli_summary['Tests Conducted'].apply(lambda x: f"{x:,.0f}")
            df_ecoli_summary['Tests Passed'] = df_ecoli_summary['Tests Passed'].apply(lambda x: f"{x:,.0f}")
            df_ecoli_summary['Pass Rate %'] = df_ecoli_summary['Pass Rate %'].apply(lambda x: f"{x:.1f}%")
            st.dataframe(df_ecoli_summary.sort_values(by='Pass Rate %', ascending=False), hide_index=True, use_container_width=True)

        else:
            st.info("No E. Coli test data available for selected filters.")
            


    st.markdown("---")


    # --- SECTION 3: Sanitation Access and Coverage (Multiple Tabs) ---
    
    st.markdown("## 3. Sanitation Access and Coverage 🚽")

    tab_sewer_trend, tab_toilets = st.tabs(["Sewer & Household Coverage Trend", "Public Toilet Access"])

    with tab_sewer_trend:
        # Sewer Connections vs Households Trend 
        df_san_trend = filtered_sanitation.groupby(
            pd.Grouper(key='date', freq='MS')
        )[['households', 'sewer_connections', 'public_toilets']].max().reset_index()
        
        df_san_trend['Sewer_Coverage_%'] = (
            df_san_trend['sewer_connections'] / df_san_trend['households'] * 100
        )

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_trace(go.Scatter(x=df_san_trend['date'], y=df_san_trend['households'], name='Households', mode='lines', line=dict(color='#ffd93d', width=3)), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_san_trend['date'], y=df_san_trend['sewer_connections'], name='Sewer Connections', mode='lines+markers', line=dict(color='#95e1d3', width=3)), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_san_trend['date'], y=df_san_trend['Sewer_Coverage_%'], name='Sewer Coverage %', mode='lines', line=dict(color='#ff6b6b', dash='dot'), line_shape='spline'), secondary_y=True)

        fig.update_layout(
            title_text="Sanitation Coverage Trend (Connections vs Households)", height=450, hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8f8f2'), 
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#f8f8f2'))
        )
        fig.update_yaxes(title_text="Count", secondary_y=False, color='#f8f8f2', tickformat=',')
        fig.update_yaxes(title_text="Coverage Percentage (%)", secondary_y=True, range=[0, 100], color='#ff6b6b')
        st.plotly_chart(fig, use_container_width=True)
        
        # Explainer
        add_chart_explainer(
            "Sanitation Coverage Trend (Connections vs Households)", 
            "The yellow line shows the total number of Households (left axis). The blue line shows the number of Sewer Connections (left axis). The dotted red line tracks the calculated Sewer Coverage Percentage (right axis), which is Connections / Households. The trend often shows a growing gap between household growth and infrastructure expansion."
        )

        # Summary Table
        st.markdown("**Coverage Trend Summary (Latest)**")
        df_trend_summary = df_san_trend[['date', 'households', 'sewer_connections', 'Sewer_Coverage_%']].copy()
        df_trend_summary.columns = ['Date', 'Households', 'Connections', 'Coverage %']
        df_trend_summary['Households'] = df_trend_summary['Households'].apply(lambda x: f"{x:,.0f}")
        df_trend_summary['Connections'] = df_trend_summary['Connections'].apply(lambda x: f"{x:,.0f}")
        df_trend_summary['Coverage %'] = df_trend_summary['Coverage %'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(df_trend_summary.sort_values(by='Date', ascending=False).head(10), hide_index=True, use_container_width=True)


    with tab_toilets:
        df_toilet_country = filtered_sanitation.groupby('country').agg(
            total_public_toilets=('public_toilets', 'max'),
            max_households=('households', 'max')
        ).reset_index().fillna(0)

        df_toilet_country['Toilets_per_1000_HH'] = (
            df_toilet_country['total_public_toilets'] / df_toilet_country['max_households'] * 1000
        ).replace([float('inf'), -float('inf')], 0).fillna(0)
        
        df_toilet_country = df_toilet_country.sort_values(by='Toilets_per_1000_HH', ascending=False)

        if not df_toilet_country.empty:
            fig_toilets = px.bar(
                df_toilet_country, y='country', x='Toilets_per_1000_HH', orientation='h',
                title='Public Toilets per 1,000 Households by Country (Latest)',
                labels={'Toilets_per_1000_HH': 'Toilets per 1,000 HH', 'country': 'Country'},
                text='Toilets_per_1000_HH', color='Toilets_per_1000_HH', color_continuous_scale=px.colors.sequential.Viridis
            )
            fig_toilets.update_traces(texttemplate='%{text:.2f}', textposition='outside', textfont=dict(color='#f8f8f2'))
            fig_toilets.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8f8f2'), showlegend=False)
            st.plotly_chart(fig_toilets, use_container_width=True)
            
            # Explainer
            add_chart_explainer("Public Toilets per 1,000 Households by Country", "Measures the access rate to public sanitation facilities by normalizing the total number of public toilets by the number of households (per 1,000) for each country. This indicator is crucial for providing equitable access, particularly in high-density urban zones or areas lacking private connections.")

            # Summary Table
            st.markdown("**Public Toilet Access Summary**")
            df_toilet_summary = df_toilet_country[['country', 'total_public_toilets', 'max_households', 'Toilets_per_1000_HH']].copy()
            df_toilet_summary.columns = ['Country', 'Total Toilets', 'Max Households', 'Toilets per 1,000 HH']
            df_toilet_summary['Total Toilets'] = df_toilet_summary['Total Toilets'].apply(lambda x: f"{x:,.0f}")
            df_toilet_summary['Max Households'] = df_toilet_summary['Max Households'].apply(lambda x: f"{x:,.0f}")
            df_toilet_summary['Toilets per 1,000 HH'] = df_toilet_summary['Toilets per 1,000 HH'].apply(lambda x: f"{x:.2f}")
            st.dataframe(df_toilet_summary.sort_values(by='Toilets per 1,000 HH', ascending=False), hide_index=True, use_container_width=True)

        else:
            st.info("No data available for Public Toilet Access.")
            


    st.markdown("---")


    # --- SECTION 4: Wastewater & Sludge Management (Multiple Tabs) ---
    
    st.markdown("## 4. Wastewater & Sludge Management ♻️")

    tab_ww, tab_fs = st.tabs(["Wastewater Flow and Treatment", "Fecal Sludge Management Trend"])

    # Wastewater Flow and Treatment - Chart 4.1
    with tab_ww:
        df_ww_flow = filtered_sanitation.groupby('date')[[
            'ww_collected', 'ww_treated', 'ww_reused'
        ]].sum().reset_index()
        
        ww_cols = ['ww_collected', 'ww_treated', 'ww_reused']
        df_ww_melt = df_ww_flow.melt(
            id_vars=['date'], value_vars=ww_cols, var_name='WW Flow Stage', value_name='Volume'
        )
        
        fig_ww = px.bar(
            df_ww_melt, x='date', y='Volume', color='WW Flow Stage',
            title="Wastewater Collection, Treatment, and Reuse Trend",
            barmode='group', labels={'Volume': 'Volume (m³)', 'date': 'Date'},
            color_discrete_map={
                'ww_collected': '#5681d0', 'ww_treated': '#6bcf7f', 'ww_reused': '#95e1d3'
            }
        )
        
        fig_ww.update_layout(
            height=450, hovermode='x unified', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8f8f2'), 
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#f8f8f2'))
        )
        fig_ww.update_yaxes(tickformat=',.0f')
        
        st.plotly_chart(fig_ww, use_container_width=True)

        # Explainer
        add_chart_explainer("Wastewater Collection, Treatment, and Reuse Trend", "A group bar chart showing the volume of collected, treated, and reused wastewater over time. The primary objective is to maximize the treated volume relative to the collected volume, minimizing untreated discharge into the environment.")

        # Summary Table
        st.markdown("**Wastewater Flow Summary (Latest)**")
        df_ww_flow_summary = df_ww_flow.copy()
        df_ww_flow_summary.columns = ['Date', 'Collected (m³)', 'Treated (m³)', 'Reused (m³)']
        for col in df_ww_flow_summary.columns[1:]:
             df_ww_flow_summary[col] = df_ww_flow_summary[col].apply(lambda x: f"{x:,.0f}")
        st.dataframe(df_ww_flow_summary.sort_values(by='Date', ascending=False).head(10), hide_index=True, use_container_width=True)


    # Fecal Sludge Management Trend - Chart 4.2
    with tab_fs:
        df_fs_flow = filtered_sanitation.groupby('date')[[
            'hh_emptied', 'fs_treated', 'fs_reused'
        ]].sum().reset_index()

        fs_cols = ['hh_emptied', 'fs_treated', 'fs_reused']
        df_fs_melt = df_fs_flow.melt(
            id_vars=['date'], value_vars=fs_cols, var_name='FS Management Stage', value_name='Volume'
        )
        
        fig_fs = px.line(
            df_fs_melt, x='date', y='Volume', color='FS Management Stage',
            title="Fecal Sludge Management Trend (Emptied, Treated, and Reused)",
            labels={'Volume': 'Volume (m³)', 'date': 'Date'},
            color_discrete_map={
                'hh_emptied': '#ffb5b5', 'fs_treated': '#94d2bd', 'fs_reused': '#00bfa5'
            }
        )
        
        fig_fs.update_layout(
            height=450, hovermode='x unified', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8f8f2'), 
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#f8f8f2'))
        )
        fig_fs.update_yaxes(tickformat=',.0f')
        
        st.plotly_chart(fig_fs, use_container_width=True)
        
        # Explainer
        add_chart_explainer("Fecal Sludge Management Trend (Emptied, Treated, and Reused)", "A line chart showing the monthly trend of fecal sludge volume. Treatment and reuse volumes are critical for circular economy models in sanitation, often involving conversion into useful by-products like soil conditioner.")

        # Summary Table
        st.markdown("**Fecal Sludge Flow Summary (Latest)**")
        df_fs_flow_summary = df_fs_flow.copy()
        df_fs_flow_summary.columns = ['Date', 'HH Emptied (m³)', 'Treated (m³)', 'Reused (m³)']
        for col in df_fs_flow_summary.columns[1:]:
             df_fs_flow_summary[col] = df_fs_flow_summary[col].apply(lambda x: f"{x:,.0f}")
        st.dataframe(df_fs_flow_summary.sort_values(by='Date', ascending=False).head(10), hide_index=True, use_container_width=True)


    st.markdown("---")


    # --- SECTION 5: Workforce and Operational Ratios (Four Flat Tabs, reordered) ---
    
    st.markdown("## 5. Workforce and Operational Ratios 👨‍💼")

    # Reorder tabs: Staffing, Demographics, WW Treatment, FS Treatment
    tab_staff, tab_demographics, tab_ww_treat, tab_fs_treat = st.tabs(
        ["Staffing Efficiency", "Workforce Demographics", "WW Treatment Rate (%)", "FS Treatment Rate (%)"]
    )

    # Prepare the common DataFrame once
    df_eff_country = filtered_sanitation.groupby('country').agg(
        households=('households', 'max'),
        workforce=('workforce', 'sum'),
        ww_collected=('ww_collected', 'sum'),
        ww_treated=('ww_treated', 'sum'),
        hh_emptied=('hh_emptied', 'sum'), 
        fs_treated=('fs_treated', 'sum'), 
        f_workforce=('f_workforce', 'sum') 
    ).reset_index()
    
    # Staffing calculation
    df_eff_country['Staff_per_1000_HH'] = (
        df_eff_country['workforce'] / df_eff_country['households'] * 1000
    ).replace([float('inf'), -float('inf')], 0).fillna(0)

    # WW Treatment calculation
    df_eff_country['WW_Treat_Rate'] = (
        df_eff_country['ww_treated'] / df_eff_country['ww_collected'] * 100
    ).replace([float('inf'), -float('inf')], 0).fillna(0).clip(0, 100)

    # FS Treatment calculation (Using Factor)
    df_eff_country['FS_Treat_Factor'] = (
        df_eff_country['fs_treated'] / df_eff_country['hh_emptied']
    ).replace([float('inf'), -float('inf')], 0).fillna(0)


    with tab_staff:
        # Staffing Efficiency Chart
        fig_staff = px.bar(
            df_eff_country.sort_values('Staff_per_1000_HH'), y='country', x='Staff_per_1000_HH', orientation='h',
            title='Workforce Staffing Efficiency (per 1,000 Households)',
            labels={'Staff_per_1000_HH': 'Staff per 1,000 HH', 'country': 'Country'},
            text='Staff_per_1000_HH', color='Staff_per_1000_HH', color_continuous_scale=px.colors.sequential.Tealgrn
        )
        fig_staff.update_traces(texttemplate='%{text:.1f}', textposition='outside', textfont=dict(color='#f8f8f2'))
        fig_staff.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8f8f2'), showlegend=False)
        st.plotly_chart(fig_staff, use_container_width=True)

        # Explainer
        add_chart_explainer("Workforce Staffing Efficiency (per 1,000 Households)", "Compares the workforce efficiency across countries by calculating the ratio of total workforce staff to every 1,000 households served. Lower ratios can indicate higher efficiency and productivity, but excessively low figures may suggest understaffing.")

        # Summary Table
        st.markdown("**Staffing Efficiency Summary**")
        df_staff_summary = df_eff_country[['country', 'workforce', 'households', 'Staff_per_1000_HH']].copy()
        df_staff_summary.columns = ['Country', 'Total Workforce', 'Max Households', 'Staff per 1,000 HH']
        df_staff_summary['Total Workforce'] = df_staff_summary['Total Workforce'].apply(lambda x: f"{x:,.0f}")
        df_staff_summary['Max Households'] = df_staff_summary['Max Households'].apply(lambda x: f"{x:,.0f}")
        df_staff_summary['Staff per 1,000 HH'] = df_staff_summary['Staff per 1,000 HH'].apply(lambda x: f"{x:.1f}")
        st.dataframe(df_staff_summary.sort_values(by='Staff per 1,000 HH', ascending=False), hide_index=True, use_container_width=True)

    
    with tab_demographics:
        df_gender_country = df_eff_country.copy()
        
        df_gender_country['Female_%'] = (
            df_gender_country['f_workforce'] / df_gender_country['workforce'] * 100
        ).fillna(0)
        df_gender_country['Male_%'] = 100 - df_gender_country['Female_%']
        
        df_gender_melt = df_gender_country.melt(
            id_vars=['country'], value_vars=['Female_%', 'Male_%'], var_name='Gender_Category', value_name='Percentage'
        )

        fig_gender = px.bar(
            df_gender_melt, x='country', y='Percentage', color='Gender_Category',
            title='Workforce Gender Split by Country', labels={'Percentage': 'Percentage (%)', 'country': 'Country'},
            barmode='stack', color_discrete_map={'Female_%': '#E68A9E', 'Male_%': '#5681d0'}
        )
        
        fig_gender.update_layout(
            height=450, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8f8f2'), 
            yaxis=dict(range=[0, 100]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#f8f8f2'))
        )
        st.plotly_chart(fig_gender, use_container_width=True)
        
        # Explainer
        add_chart_explainer("Workforce Gender Split by Country", "A stacked bar chart showing the percentage breakdown of the workforce by gender for each country. Promoting gender balance, especially in technical and leadership roles, is a common goal for utility modernization.")

        # Summary table (as requested, this was already good)
        st.markdown("**Workforce Summary**")
        df_gender_summary = df_gender_country[['country', 'workforce', 'f_workforce', 'Female_%']].copy()
        df_gender_summary.columns = ['Country', 'Total Workforce', 'Female Staff', 'Female %']
        df_gender_summary['Total Workforce'] = df_gender_summary['Total Workforce'].apply(lambda x: f"{x:,.0f}")
        df_gender_summary['Female Staff'] = df_gender_summary['Female Staff'].apply(lambda x: f"{x:,.0f}")
        df_gender_summary['Female %'] = df_gender_summary['Female %'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(df_gender_summary, hide_index=True, use_container_width=True)


    with tab_ww_treat:
        # Wastewater Treatment Efficiency Chart
        fig_treat = px.bar(
            df_eff_country.sort_values('WW_Treat_Rate'), y='country', x='WW_Treat_Rate', orientation='h',
            title='Wastewater Treatment Rate (%) by Country',
            labels={'WW_Treat_Rate': 'Treatment Rate (%)', 'country': 'Country'},
            text='WW_Treat_Rate', color='WW_Treat_Rate', color_continuous_scale=px.colors.sequential.Plasma
        )
        fig_treat.update_traces(texttemplate='%{text:.1f}%', textposition='outside', textfont=dict(color='#f8f8f2'))
        fig_treat.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8f8f2'), showlegend=False)
        st.plotly_chart(fig_treat, use_container_width=True)

        # Explainer
        add_chart_explainer("Wastewater Treatment Rate (%) by Country", "Shows the total percentage of collected wastewater that is subsequently treated in each country (Treated WW / Collected WW). Rates below 80% often indicate insufficient plant capacity or operational issues, leading to untreated discharge.")

        # Summary Table
        st.markdown("**WW Treatment Rate Summary**")
        df_ww_summary = df_eff_country[['country', 'ww_collected', 'ww_treated', 'WW_Treat_Rate']].copy()
        df_ww_summary.columns = ['Country', 'WW Collected (m³)', 'WW Treated (m³)', 'Treatment Rate %']
        df_ww_summary['WW Collected (m³)'] = df_ww_summary['WW Collected (m³)'].apply(lambda x: f"{x:,.0f}")
        df_ww_summary['WW Treated (m³)'] = df_ww_summary['WW Treated (m³)'].apply(lambda x: f"{x:,.0f}")
        df_ww_summary['Treatment Rate %'] = df_ww_summary['Treatment Rate %'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(df_ww_summary.sort_values(by='Treatment Rate %', ascending=False), hide_index=True, use_container_width=True)
        
        
    with tab_fs_treat:
        # Fecal Sludge Treatment Efficiency Chart (Using Factor)
        fig_fs_treat = px.bar(
            df_eff_country.sort_values('FS_Treat_Factor'), y='country', x='FS_Treat_Factor', orientation='h',
            title='Fecal Sludge Treatment Factor (Treated/Emptied Volume) by Country',
            labels={'FS_Treat_Factor': 'Treatment Factor', 'country': 'Country'},
            text='FS_Treat_Factor', color='FS_Treat_Factor', color_continuous_scale=px.colors.sequential.Mint
        )
        fig_fs_treat.update_traces(texttemplate='%{text:.2f}', textposition='outside', textfont=dict(color='#f8f8f2'))
        fig_fs_treat.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8f8f2'), showlegend=False)
        st.plotly_chart(fig_fs_treat, use_container_width=True)

        # Explainer
        add_chart_explainer("Fecal Sludge Treatment Factor (Treated/Emptied Volume) by Country", "Shows the ratio of total fecal sludge treated to the total volume collected from household emptying. A factor greater than 1.0 means the treatment facility is managing more sludge volume than what is reported through household emptying services, indicating treatment of external or third-party collected sludge.")

        # Summary Table
        st.markdown("**FS Treatment Factor Summary**")
        df_fs_summary = df_eff_country[['country', 'hh_emptied', 'fs_treated', 'FS_Treat_Factor']].copy()
        df_fs_summary.columns = ['Country', 'HH Emptied (m³)', 'FS Treated (m³)', 'Treatment Factor']
        df_fs_summary['HH Emptied (m³)'] = df_fs_summary['HH Emptied (m³)'].apply(lambda x: f"{x:,.0f}")
        df_fs_summary['FS Treated (m³)'] = df_fs_summary['FS Treated (m³)'].apply(lambda x: f"{x:,.0f}")
        df_fs_summary['Treatment Factor'] = df_fs_summary['Treatment Factor'].apply(lambda x: f"{x:.2f}")
        st.dataframe(df_fs_summary.sort_values(by='Treatment Factor', ascending=False), hide_index=True, use_container_width=True)
        

    # --- Access Datasets ---

    st.markdown("---")
    st.markdown("### Access Datasets")
    
    with st.expander("Click to view water_service.csv", expanded=False): 
        st.dataframe(filtered_water, use_container_width=True, hide_index=True)

    with st.expander("Click to view s_service.csv", expanded=False): 
        st.dataframe(filtered_sanitation, use_container_width=True, hide_index=True)


# --- Standalone Execution Block ---
if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="Service Delivery Dashboard")
    st.sidebar.title("Standalone Filters (Used only when running this file directly)")
    
    df_water, df_sanitation = load_data()
    
    if not df_water.empty and not df_sanitation.empty:
        all_countries = sorted(df_water['country'].unique().tolist())
        selected_countries = st.sidebar.multiselect("Select Countries", all_countries)
        
        min_year = int(min(df_water['date'].dt.year.min(), df_sanitation['date'].dt.year.min()))
        max_year = int(max(df_water['date'].dt.year.max(), df_sanitation['date'].dt.year.max()))
        year_range = st.sidebar.slider("Select Year Range", min_year, max_year, (min_year, max_year))
        
        show(selected_countries, year_range)
    else:
        st.error("Cannot run standalone. Please check data files.")
