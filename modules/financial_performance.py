import streamlit as st
import pandas as pd
import plotly.express as px
from components.container import card_container
import plotly.graph_objects as go
from plotly.subplots import make_subplots


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
    
    # Normalize country names in financial data too
    if 'country' in df_financial.columns:
        df_financial['country'] = df_financial['country'].str.title()
    
    return df_billing, df_financial


def show(selected_countries, year_range=None):
    st.title("Financial Performance")
    
    df_billing, df_financial = load_data()
    
    # Apply filters to both datasets
    filtered_billing = df_billing.copy()
    filtered_financial = df_financial.copy()
    
    # Filter by selected countries from global filter
    if selected_countries:
        filtered_billing = filtered_billing[filtered_billing['country'].isin(selected_countries)]
        if 'country' in filtered_financial.columns:
            filtered_financial = filtered_financial[filtered_financial['country'].isin(selected_countries)]
    
    # Filter by year range from global filter
    if year_range:
        start_year, end_year = year_range
        filtered_billing = filtered_billing[
            (filtered_billing['date'].dt.year >= start_year) & 
            (filtered_billing['date'].dt.year <= end_year)
        ]
        filtered_financial = filtered_financial[
            (filtered_financial['date_MMYY'].dt.year >= start_year) & 
            (filtered_financial['date_MMYY'].dt.year <= end_year)
        ]

    # Calculate KPIs using FILTERED data
    total_revenue = filtered_billing['paid'].sum()
    total_billed = filtered_billing['billed'].sum()
    collection_rate = (total_revenue / total_billed * 100) if total_billed > 0 else 0
    
    total_sewer_revenue = filtered_financial['sewer_revenue'].sum() if len(filtered_financial) > 0 else 0
    total_opex = filtered_financial['opex'].sum() if len(filtered_financial) > 0 else 0
    cost_recovery_rate = (total_sewer_revenue / total_opex * 100) if total_opex > 0 else 0
    
    outstanding = total_billed - total_revenue
    total_customers = filtered_billing['customer_id'].nunique()
    avg_revenue_per_customer = (total_revenue / total_customers) if total_customers > 0 else 0

    # KPIs Display
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with card_container(key="kpi_metric1"):
            st.metric("Total Revenue", f"${total_revenue:,.0f}")
    
    with col2:
        with card_container(key="kpi_metric2"):
            st.metric("Collection Rate", f"{collection_rate:.1f}%")

    with col3:
        with card_container(key="kpi_metric3"):
            st.metric("Cost Recovery Rate", f"{cost_recovery_rate:.1f}%")
    
    col1, col2, col3 = st.columns(3)

    with col1: 
        with card_container(key="kpi_metric4"): 
            st.metric("Outstanding", f"${outstanding:,.0f}")

    with col2: 
        with card_container(key="kpi_metric5"): 
            st.metric("Active Customers", f"{total_customers:,}")

    with col3: 
        with card_container(key="kpi_metric6"): 
            st.metric("Avg Revenue/Customer", f"${avg_revenue_per_customer:,.0f}")

    # ========================================================================
    # SECTION 1: Revenue Breakdown & Trends
    # ========================================================================
    st.markdown("### Revenue Breakdown & Trends")

    tab1, tab2 = st.tabs(["Monthly Revenue", "Revenue Breakdown"])

    with tab1:
        # Monthly revenue trend by country
        monthly_by_country = filtered_billing.groupby(
            [pd.Grouper(key='date', freq='MS'), 'country'], 
            dropna=False
        ).agg({'paid': 'sum'}).reset_index()
        
        monthly_by_country = monthly_by_country.dropna(subset=['country'])

        fig_revenue = px.line(
            monthly_by_country,
            x='date',
            y='paid',
            color='country',
            title='Monthly Revenue Trend by Country',
            labels={'date': 'Month', 'paid': 'Revenue ($)', 'country': 'Country'},
            markers=True
        )
        
        fig_revenue.update_layout(
            height=450,
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8f8f2'),
            title_font=dict(color='#f8f8f2'),
            xaxis=dict(
                showgrid=True, 
                gridcolor='rgba(128,128,128,0.2)',
                color='#f8f8f2',
                title_font=dict(color='#f8f8f2')
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor='rgba(128,128,128,0.2)', 
                tickprefix='$', 
                tickformat=',.0f',
                color='#f8f8f2',
                title_font=dict(color='#f8f8f2')
            ),
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="right", 
                x=1,
                font=dict(color='#f8f8f2')
            )
        )
        
        fig_revenue.update_traces(line=dict(width=2.5), marker=dict(size=6))
        
        st.plotly_chart(fig_revenue, use_container_width=True)

    with tab2:
        # Revenue breakdown by country
        country_revenue = filtered_billing.groupby('country').agg({
            'paid': 'sum',
            'billed': 'sum',
            'customer_id': 'nunique'
        }).reset_index()
        
        country_revenue['collection_rate'] = (country_revenue['paid'] / country_revenue['billed'] * 100)
        country_revenue = country_revenue.sort_values('paid', ascending=True)
        
        fig = px.bar(
            country_revenue,
            y='country',
            x='paid',
            orientation='h',
            title='Total Revenue by Country',
            labels={'paid': 'Revenue ($)', 'country': 'Country'},
            text='paid'
        )
        
        fig.update_traces(
            texttemplate='$%{text:,.0f}', 
            textposition='outside',
            marker_color='#5681d0',
            textfont=dict(color='#f8f8f2')
        )
        
        fig.update_layout(
            height=400,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8f8f2'),
            title_font=dict(color='#f8f8f2'),
            xaxis=dict(
                showgrid=True, 
                gridcolor='rgba(128,128,128,0.2)', 
                tickprefix='$', 
                tickformat=',.0f',
                color='#f8f8f2',
                title_font=dict(color='#f8f8f2')
            ),
            yaxis=dict(
                showgrid=False,
                color='#f8f8f2',
                title_font=dict(color='#f8f8f2')
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display table
        st.markdown("**Country Performance Summary**")
        country_display = country_revenue.sort_values('paid', ascending=False).copy()
        country_display['paid'] = country_display['paid'].apply(lambda x: f"${x:,.0f}")
        country_display['billed'] = country_display['billed'].apply(lambda x: f"${x:,.0f}")
        country_display['collection_rate'] = country_display['collection_rate'].apply(lambda x: f"{x:.1f}%")
        country_display.columns = ['Country', 'Revenue', 'Billed', 'Customers', 'Collection Rate']
        
        st.dataframe(country_display, hide_index=True, use_container_width=True)

    # ========================================================================
    # SECTION 2: Collection Efficiency & Payment Analysis
    # ========================================================================
    st.markdown("### Collection Efficiency & Payment Analysis")

    tab1, tab2 = st.tabs(["Billed vs Paid Analysis", "Collection Rate by Country"])
    
    with tab1:
        # Prepare monthly data
        monthly_billing = (
            filtered_billing
            .groupby(filtered_billing['date'].dt.to_period('M'))
            .agg({'billed': 'sum', 'paid': 'sum'})
            .reset_index()
        )

        monthly_billing['month'] = monthly_billing['date'].dt.to_timestamp()
        monthly_billing['collection_rate'] = (
            monthly_billing['paid'] / monthly_billing['billed'] * 100
        )
        monthly_billing['outstanding'] = (
            monthly_billing['billed'] - monthly_billing['paid']
        )

        # Create dual-axis chart
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_trace(
            go.Bar(
                x=monthly_billing['month'],
                y=monthly_billing['billed'],
                name='Billed',
                marker_color='rgba(86, 129, 208, 0.4)',
                opacity=0.8
            ),
            secondary_y=False
        )

        fig.add_trace(
            go.Bar(
                x=monthly_billing['month'],
                y=monthly_billing['paid'],
                name='Paid',
                marker_color='#5681d0',
                opacity=0.9
            ),
            secondary_y=False
        )

        fig.add_trace(
            go.Scatter(
                x=monthly_billing['month'],
                y=monthly_billing['collection_rate'],
                name='Collection Rate',
                mode='lines+markers',
                line=dict(color='#ff6b6b', width=3),
                marker=dict(size=8)
            ),
            secondary_y=True
        )

        fig.add_hline(
            y=85,
            line_dash="dash",
            line_color="rgba(0,255,0,0.5)",
            annotation_text="Target: 85%",
            annotation_position="top left",
            annotation_font=dict(color='#f8f8f2'),
            secondary_y=True
        )

        fig.update_xaxes(
            title_text="Month",
            color='#f8f8f2',
            title_font=dict(color='#f8f8f2')
        )
        fig.update_yaxes(
            title_text="Amount ($)", 
            secondary_y=False,
            showgrid=True, 
            gridcolor='rgba(128,128,128,0.2)',
            color='#f8f8f2',
            title_font=dict(color='#f8f8f2')
        )
        fig.update_yaxes(
            title_text="Collection Rate (%)", 
            secondary_y=True, 
            range=[0, 110],
            showgrid=False,
            color='#f8f8f2',
            title_font=dict(color='#f8f8f2')
        )

        fig.update_layout(
            height=450,
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8f8f2'),
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="right", 
                x=1,
                font=dict(color='#f8f8f2')
            )
        )

        st.plotly_chart(fig, use_container_width=True)
        
        # Key insights
        col1, col2 = st.columns([1, 1])
        
        with col1:
            recent_collection = monthly_billing.tail(1)['collection_rate'].iloc[0] if len(monthly_billing) > 0 else 0
            avg_collection = monthly_billing['collection_rate'].mean()
            
            with card_container(key="insight1"):
                st.metric("Latest Collection Rate", f"{recent_collection:.1f}%")
            
        with col2:
            total_outstanding = monthly_billing.tail(1)['outstanding'].iloc[0] if len(monthly_billing) > 0 else 0
            
            with card_container(key="insight2"):
                st.metric("Current Outstanding", f"${total_outstanding:,.0f}")

    with tab2:
        # Collection rate by country - simple and clean
        country_collection = filtered_billing.groupby('country').agg({
            'billed': 'sum',
            'paid': 'sum'
        }).reset_index()
        
        country_collection['collection_rate'] = (
            country_collection['paid'] / country_collection['billed'] * 100
        )
        country_collection = country_collection.sort_values('collection_rate', ascending=True)
        
        fig = px.bar(
            country_collection,
            y='country',
            x='collection_rate',
            orientation='h',
            title='Collection Rate by Country',
            labels={'collection_rate': 'Collection Rate (%)', 'country': 'Country'},
            text='collection_rate',
            color='collection_rate',
            color_continuous_scale=['#ff6b6b', '#ffd93d', '#6bcf7f'],
            range_color=[0, 100]
        )
        
        fig.update_traces(
            texttemplate='%{text:.1f}%', 
            textposition='outside',
            textfont=dict(color='#f8f8f2')
        )
        
        fig.add_vline(
            x=85, 
            line_dash="dash", 
            line_color="rgba(255,255,255,0.5)",
            annotation_text="Target: 85%",
            annotation_font=dict(color='#f8f8f2')
        )
        
        fig.update_layout(
            height=400,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8f8f2'),
            title_font=dict(color='#f8f8f2'),
            xaxis=dict(
                showgrid=True, 
                gridcolor='rgba(128,128,128,0.2)', 
                range=[0, 110],
                color='#f8f8f2',
                title_font=dict(color='#f8f8f2')
            ),
            yaxis=dict(
                showgrid=False,
                color='#f8f8f2',
                title_font=dict(color='#f8f8f2')
            ),
            showlegend=False,
            coloraxis_colorbar=dict(
                title=dict(text="Rate (%)", font=dict(color='#f8f8f2')),
                tickfont=dict(color='#f8f8f2')
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)

    # ========================================================================
    # SECTION 3: Customer Segmentation & Behavior
    # ========================================================================
    st.markdown("### Customer Segmentation & Behavior")

    tab1, tab2 = st.tabs(["Consumption vs Payment Matrix", "Customer Value Segmentation"])

    with tab1:
        # Customer-level analysis
        customer_analysis = filtered_billing.groupby('customer_id').agg({
            'consumption_m3': 'mean',
            'billed': 'sum',
            'paid': 'sum'
        }).reset_index()
        
        customer_analysis['payment_rate'] = (
            customer_analysis['paid'] / customer_analysis['billed'] * 100
        ).clip(0, 100)
        
        # Sample for visualization (too many points will slow down)
        sample_size = min(2000, len(customer_analysis))
        customer_sample = customer_analysis.sample(sample_size) if len(customer_analysis) > sample_size else customer_analysis
        
        fig = px.scatter(
            customer_sample,
            x='consumption_m3',
            y='payment_rate',
            size='billed',
            color='payment_rate',
            color_continuous_scale=['#ff6b6b', '#ffd93d', '#6bcf7f'],
            title=f'Customer Payment Behavior (Sample: {sample_size:,} customers)',
            labels={
                'consumption_m3': 'Avg Consumption (m³)',
                'payment_rate': 'Payment Rate (%)',
                'billed': 'Total Billed'
            },
            hover_data={'billed': ':$,.0f'}
        )
        
        fig.add_hline(
            y=85, 
            line_dash="dash", 
            line_color="rgba(255,255,255,0.3)",
            annotation_text="Target: 85%",
            annotation_font=dict(color='#f8f8f2')
        )
        
        fig.update_layout(
            height=450,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8f8f2'),
            title_font=dict(color='#f8f8f2'),
            xaxis=dict(
                showgrid=True, 
                gridcolor='rgba(128,128,128,0.2)',
                color='#f8f8f2',
                title_font=dict(color='#f8f8f2')
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor='rgba(128,128,128,0.2)',
                color='#f8f8f2',
                title_font=dict(color='#f8f8f2')
            ),
            coloraxis_colorbar=dict(
                title=dict(text="Rate (%)", font=dict(color='#f8f8f2')),
                tickfont=dict(color='#f8f8f2')
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # Customer segmentation
        customer_analysis['segment'] = 'Standard'
        customer_analysis.loc[
            (customer_analysis['payment_rate'] >= 90) & (customer_analysis['billed'] > customer_analysis['billed'].median()),
            'segment'
        ] = 'Premium'
        customer_analysis.loc[
            (customer_analysis['payment_rate'] >= 85) & (customer_analysis['payment_rate'] < 90),
            'segment'
        ] = 'Good'
        customer_analysis.loc[
            (customer_analysis['payment_rate'] >= 70) & (customer_analysis['payment_rate'] < 85),
            'segment'
        ] = 'At Risk'
        customer_analysis.loc[
            customer_analysis['payment_rate'] < 70,
            'segment'
        ] = 'Problem'
        
        # Segment summary
        segment_summary = customer_analysis.groupby('segment').agg({
            'customer_id': 'count',
            'paid': 'sum',
            'payment_rate': 'mean'
        }).reset_index()
        
        segment_summary.columns = ['Segment', 'Customer Count', 'Total Revenue', 'Avg Payment Rate']
        segment_summary['Revenue %'] = (segment_summary['Total Revenue'] / segment_summary['Total Revenue'].sum() * 100)
        
        # Reorder segments
        segment_order = ['Premium', 'Good', 'Standard', 'At Risk', 'Problem']
        segment_summary['Segment'] = pd.Categorical(segment_summary['Segment'], categories=segment_order, ordered=True)
        segment_summary = segment_summary.sort_values('Segment')
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart
            fig = px.pie(
                segment_summary,
                values='Customer Count',
                names='Segment',
                title='Customer Distribution by Segment',
                color='Segment',
                color_discrete_map={
                    'Premium': '#6bcf7f',
                    'Good': '#95e1d3',
                    'Standard': '#5681d0',
                    'At Risk': '#ffd93d',
                    'Problem': '#ff6b6b'
                }
            )
            
            fig.update_layout(
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f8f8f2'),
                title_font=dict(color='#f8f8f2'),
                legend=dict(font=dict(color='#f8f8f2'))
            )
            
            fig.update_traces(textfont=dict(color='#ffffff'))
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Bar chart of revenue
            fig = px.bar(
                segment_summary,
                x='Segment',
                y='Total Revenue',
                title='Revenue by Customer Segment',
                text='Total Revenue',
                color='Segment',
                color_discrete_map={
                    'Premium': '#6bcf7f',
                    'Good': '#95e1d3',
                    'Standard': '#5681d0',
                    'At Risk': '#ffd93d',
                    'Problem': '#ff6b6b'
                }
            )
            
            fig.update_traces(
                texttemplate='$%{text:,.0f}', 
                textposition='outside',
                textfont=dict(color='#f8f8f2')
            )
            
            fig.update_layout(
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f8f8f2'),
                title_font=dict(color='#f8f8f2'),
                xaxis=dict(
                    showgrid=False,
                    color='#f8f8f2',
                    title_font=dict(color='#f8f8f2')
                ),
                yaxis=dict(
                    showgrid=True, 
                    gridcolor='rgba(128,128,128,0.2)', 
                    tickprefix='$', 
                    tickformat=',.0f',
                    color='#f8f8f2',
                    title_font=dict(color='#f8f8f2')
                ),
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Summary table
        st.markdown("**Segment Performance Summary**")
        display_segment = segment_summary.copy()
        display_segment['Total Revenue'] = display_segment['Total Revenue'].apply(lambda x: f"${x:,.0f}")
        display_segment['Avg Payment Rate'] = display_segment['Avg Payment Rate'].apply(lambda x: f"{x:.1f}%")
        display_segment['Revenue %'] = display_segment['Revenue %'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(display_segment, hide_index=True, use_container_width=True)

    # ========================================================================
    # SECTION 4: Sewer Service & Financial Performance
    # ========================================================================
    st.markdown("### Sewer Service & Financial Performance")

    if len(filtered_financial) > 0:
        tab1, tab2 = st.tabs(["Cost Recovery by City", "Revenue vs Opex Efficiency"])
        
        with tab1:
            # Cost recovery by city
            if 'city' in filtered_financial.columns:
                city_financial = filtered_financial.groupby(['city', 'country']).agg({
                    'sewer_revenue': 'sum',
                    'opex': 'sum'
                }).reset_index()
                
                city_financial['cost_recovery'] = (
                    city_financial['sewer_revenue'] / city_financial['opex'] * 100
                )
                city_financial = city_financial.sort_values('cost_recovery', ascending=True).tail(20)
                
                fig = px.bar(
                    city_financial,
                    y='city',
                    x='cost_recovery',
                    color='country',
                    orientation='h',
                    title='Cost Recovery Rate by City (Top 20)',
                    labels={'cost_recovery': 'Cost Recovery (%)', 'city': 'City'},
                    text='cost_recovery'
                )
                
                fig.update_traces(
                    texttemplate='%{text:.1f}%', 
                    textposition='outside',
                    textfont=dict(color='#f8f8f2')
                )
                
                fig.add_vline(
                    x=100, 
                    line_dash="dash", 
                    line_color="rgba(255,255,255,0.5)",
                    annotation_text="Break-even: 100%",
                    annotation_font=dict(color='#f8f8f2')
                )
                
                fig.update_layout(
                    height=600,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#f8f8f2'),
                    title_font=dict(color='#f8f8f2'),
                    xaxis=dict(
                        showgrid=True, 
                        gridcolor='rgba(128,128,128,0.2)',
                        color='#f8f8f2',
                        title_font=dict(color='#f8f8f2')
                    ),
                    yaxis=dict(
                        showgrid=False,
                        color='#f8f8f2',
                        title_font=dict(color='#f8f8f2')
                    ),
                    legend=dict(
                        orientation="h", 
                        yanchor="bottom", 
                        y=1.02, 
                        xanchor="right", 
                        x=1,
                        font=dict(color='#f8f8f2')
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("City-level data not available in financial dataset")

        with tab2:
            # Revenue vs Opex scatter
            if 'city' in filtered_financial.columns:
                city_efficiency = filtered_financial.groupby(['city', 'country']).agg({
                    'sewer_revenue': 'sum',
                    'opex': 'sum',
                    'sewer_billed': 'sum'
                }).reset_index()
                
                fig = px.scatter(
                    city_efficiency,
                    x='opex',
                    y='sewer_revenue',
                    size='sewer_billed',
                    color='country',
                    hover_data=['city'],
                    title='Revenue vs Operating Costs',
                    labels={
                        'opex': 'Operating Expenses ($)',
                        'sewer_revenue': 'Sewer Revenue ($)',
                        'sewer_billed': 'Customers'
                    }
                )
                
                # Add break-even line
                max_val = max(city_efficiency['opex'].max(), city_efficiency['sewer_revenue'].max())
                fig.add_trace(go.Scatter(
                    x=[0, max_val],
                    y=[0, max_val],
                    mode='lines',
                    name='Break-even',
                    line=dict(dash='dash', color='rgba(255,255,255,0.5)', width=2)
                ))
                
                fig.update_layout(
                    height=450,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#f8f8f2'),
                    title_font=dict(color='#f8f8f2'),
                    xaxis=dict(
                        showgrid=True, 
                        gridcolor='rgba(128,128,128,0.2)', 
                        tickprefix='$', 
                        tickformat=',.0f',
                        color='#f8f8f2',
                        title_font=dict(color='#f8f8f2')
                    ),
                    yaxis=dict(
                        showgrid=True, 
                        gridcolor='rgba(128,128,128,0.2)', 
                        tickprefix='$', 
                        tickformat=',.0f',
                        color='#f8f8f2',
                        title_font=dict(color='#f8f8f2')
                    ),
                    legend=dict(font=dict(color='#f8f8f2'))
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("City-level data not available in financial dataset")
    else:
        st.info("No financial service data available for selected filters")

    # ========================================================================
    # SECTION 5: Operational Cost Analysis
    # ========================================================================
    st.markdown("### Operational Cost Analysis")

    if len(filtered_financial) > 0:
        tab1, tab2 = st.tabs(["Opex Trends", "Unit Cost Analysis"])
        
        with tab1:
            # Opex over time
            monthly_opex = filtered_financial.groupby('date_MMYY').agg({
                'opex': 'sum',
                'sewer_revenue': 'sum'
            }).reset_index()
            
            monthly_opex['net_income'] = monthly_opex['sewer_revenue'] - monthly_opex['opex']
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=monthly_opex['date_MMYY'],
                y=monthly_opex['sewer_revenue'],
                name='Revenue',
                mode='lines+markers',
                line=dict(color='#6bcf7f', width=3),
                marker=dict(size=6)
            ))
            
            fig.add_trace(go.Scatter(
                x=monthly_opex['date_MMYY'],
                y=monthly_opex['opex'],
                name='Opex',
                mode='lines+markers',
                line=dict(color='#ff6b6b', width=3),
                marker=dict(size=6)
            ))
            
            fig.update_layout(
                title='Revenue vs Operating Expenses Over Time',
                xaxis_title='Month',
                yaxis_title='Amount ($)',
                height=450,
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f8f8f2'),  # ← ADD THIS
                title_font=dict(color='#f8f8f2'),  # ← ADD THIS
                xaxis=dict(
                    showgrid=True, 
                    gridcolor='rgba(128,128,128,0.2)',
                    color='#f8f8f2',  # ← ADD THIS
                    title_font=dict(color='#f8f8f2')  # ← ADD THIS
                ),
                yaxis=dict(
                    showgrid=True, 
                    gridcolor='rgba(128,128,128,0.2)', 
                    tickprefix='$', 
                    tickformat=',.0f',
                    color='#f8f8f2',  # ← ADD THIS
                    title_font=dict(color='#f8f8f2')  # ← ADD THIS
                ),
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", 
                    y=1.02, 
                    xanchor="right", 
                    x=1,
                    font=dict(color='#f8f8f2')  # ← ADD THIS
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            # Unit cost analysis
            if 'city' in filtered_financial.columns and 'sewer_length' in filtered_financial.columns:
                unit_costs = filtered_financial.groupby('city').agg({
                    'opex': 'sum',
                    'sewer_billed': 'sum',
                    'sewer_length': 'sum',
                    'san_staff': 'sum',
                    'w_staff': 'sum',
                    'sewer_revenue': 'sum'
                }).reset_index()
                
                unit_costs['opex_per_customer'] = unit_costs['opex'] / unit_costs['sewer_billed']
                unit_costs['opex_per_km'] = unit_costs['opex'] / unit_costs['sewer_length']
                unit_costs['revenue_per_staff'] = unit_costs['sewer_revenue'] / (unit_costs['san_staff'] + unit_costs['w_staff'])
                
                # Sort and take top 15
                unit_costs = unit_costs.sort_values('opex_per_customer', ascending=True).head(15)
                
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=unit_costs['city'],
                    y=unit_costs['opex_per_customer'],
                    name='Opex/Customer',
                    marker_color='#5681d0'
                ))
                
                fig.update_layout(
                    title='Operating Cost per Customer by City (Top 15)',
                    xaxis_title='City',
                    yaxis_title='Opex per Customer ($)',
                    height=450,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#f8f8f2'),  # ← ADD THIS
                    title_font=dict(color='#f8f8f2'),  # ← ADD THIS
                    xaxis=dict(
                        showgrid=False, 
                        tickangle=-45,
                        color='#f8f8f2',  # ← ADD THIS
                        title_font=dict(color='#f8f8f2')  # ← ADD THIS
                    ),
                    yaxis=dict(
                        showgrid=True, 
                        gridcolor='rgba(128,128,128,0.2)', 
                        tickprefix='$', 
                        tickformat=',.0f',
                        color='#f8f8f2',  # ← ADD THIS
                        title_font=dict(color='#f8f8f2')  # ← ADD THIS
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Summary metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    with card_container(key="unit_cost1"):
                        avg_opex_customer = unit_costs['opex_per_customer'].mean()
                        st.metric("Avg Opex/Customer", f"${avg_opex_customer:,.0f}")
                
                with col2:
                    with card_container(key="unit_cost2"):
                        avg_opex_km = unit_costs['opex_per_km'].mean()
                        st.metric("Avg Opex/km", f"${avg_opex_km:,.0f}")
                
                with col3:
                    with card_container(key="unit_cost3"):
                        avg_revenue_staff = unit_costs['revenue_per_staff'].mean()
                        st.metric("Avg Revenue/Staff", f"${avg_revenue_staff:,.0f}")
            else:
                st.info("Detailed cost breakdown not available")
    else:
        st.info("No financial service data available for selected filters")



    st.markdown("### Access Datasets")
    with st.expander("Click to view billing.csv", expanded=False): 
        st.dataframe(df_billing, use_container_width=True, hide_index=True)

    with st.expander("Click to view all_fin_service.csv", expanded=False): 
        st.dataframe(df_financial, use_container_width=True, hide_index=True)