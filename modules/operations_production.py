# modules/operations_production.py

import streamlit as st
import altair as alt
import pandas as pd
from prophet import Prophet

from . import prod_ops_preprocess_data as prep


# ---------- CACHED DATA HELPERS ----------

@st.cache_data
def get_monthly_nrw_country() -> pd.DataFrame:
    return prep.monthly_nrw_country()


@st.cache_data
def get_monthly_billing_country_zone() -> pd.DataFrame:
    return prep.monthly_billing_by("country_zone")


@st.cache_data
def get_consumption_forecast(country: str, periods: int) -> pd.DataFrame:
    """
    Build a simple Prophet model on billed consumption for the given country
    and forecast the next `periods` months.
    """
    df_country = prep.monthly_nrw_country()
    df_country = df_country[df_country["country"] == country].copy()
    df_country = df_country.sort_values("month_start")

    # Prepare data for Prophet
    df = df_country[["month_start", "billed_volume_m3"]].rename(
        columns={"month_start": "ds", "billed_volume_m3": "y"}
    )

    model = Prophet()
    model.fit(df)

    future = model.make_future_dataframe(periods=periods, freq="MS")
    forecast = model.predict(future)

    return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]


# ---------- MAIN PAGE FUNCTION (called from app.py) ----------

def production_operations_page():
    st.title("Production & Operations Dashboard")

    # Load data
    df_country = get_monthly_nrw_country()
    df_zone = get_monthly_billing_country_zone()

    # Sidebar country selector (local to this page)
    countries = sorted(df_country["country"].unique())
    selected_country = st.sidebar.selectbox("Country", countries)

    # Filter country-level data
    country_data = df_country[df_country["country"] == selected_country].copy()
    country_data = country_data.sort_values("month_start")

    if country_data.empty:
        st.warning(f"No country-level data available for {selected_country}.")
        return

    # Compute rolling averages for trend KPIs
    country_data["nrw_3m_avg"] = country_data["nrw_pct"].rolling(3).mean()
    country_data["production_3m_avg"] = country_data["production_m3"].rolling(3).mean()
    country_data["consumption_3m_avg"] = country_data["billed_volume_m3"].rolling(3).mean()
    country_data["consumption_12m_avg"] = country_data["billed_volume_m3"].rolling(12).mean()

    latest = country_data.iloc[-1]
    prev = country_data.iloc[-2] if len(country_data) > 1 else None

    # Helper for YoY change
    def compute_yoy_change(df: pd.DataFrame, col_name: str):
        latest_row = df.iloc[-1]
        year = latest_row["year"]
        month = latest_row["month"]
        prev_year_rows = df[(df["year"] == year - 1) & (df["month"] == month)]
        if prev_year_rows.empty:
            return None
        prev_val = prev_year_rows[col_name].iloc[0]
        if prev_val == 0:
            return None
        return (latest_row[col_name] - prev_val) / prev_val * 100.0

    nrw_yoy = compute_yoy_change(country_data, "nrw_pct")
    prod_yoy = compute_yoy_change(country_data, "production_m3")
    cons_yoy = compute_yoy_change(country_data, "billed_volume_m3")

    # ---------- KPI CARDS ----------

    col1, col2, col3 = st.columns(3)

    # NRW KPI
    with col1:
        nrw_value = latest["nrw_pct"]
        nrw_delta = None if nrw_yoy is None else f"{nrw_yoy:+.1f}% vs last year"
        st.metric(
            label=f"NRW (%) – {selected_country}",
            value=f"{nrw_value:.1f}%",
            delta=nrw_delta,
        )
        nrw_3m = latest["nrw_3m_avg"]
        if pd.notna(nrw_3m):
            st.caption(f"3-month avg NRW: {nrw_3m:.1f}%")

    # Production KPI
    with col2:
        prod_value = latest["production_m3"]
        prod_delta = None if prod_yoy is None else f"{prod_yoy:+.1f}% YoY"
        st.metric(
            label="Production (m³)",
            value=f"{prod_value:,.0f}",
            delta=prod_delta,
        )
        prod_3m = latest["production_3m_avg"]
        if pd.notna(prod_3m):
            st.caption(f"3-month avg production: {prod_3m:,.0f} m³")

    # Consumption KPI
    with col3:
        cons_value = latest["billed_volume_m3"]
        cons_delta = None if cons_yoy is None else f"{cons_yoy:+.1f}% YoY"
        st.metric(
            label="Billed Consumption (m³)",
            value=f"{cons_value:,.0f}",
            delta=cons_delta,
        )
        cons_3m = latest["consumption_3m_avg"]
        if pd.notna(cons_3m):
            st.caption(f"3-month avg consumption: {cons_3m:,.0f} m³")

    st.markdown("---")

    # Filter zone-level data for this country
    zone_data = df_zone[df_zone["country"] == selected_country].copy()
    zone_data = zone_data.sort_values("month_start")

    # ---------- TABS ----------

    tab_nrw, tab_prodcons, tab_forecast, tab_zone_volume, tab_zone_revenue, tab_zone_mix = st.tabs(
        [
            "NRW Overview",
            "Production vs Consumption",
            "Forecast: Consumption",
            "Zone Billed Volume",
            "Zone Revenue & Collections",
            "Zone Consumption Mix",
        ]
    )

    # -------- TAB 1: NRW OVERVIEW (COUNTRY) --------
    with tab_nrw:
        st.subheader("Monthly NRW% (Country Level)")

        chart = (
            alt.Chart(country_data)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "month_start:T",
                    title="Month",
                    axis=alt.Axis(format="%b %Y", labelAngle=-45),
                ),
                y=alt.Y("nrw_pct:Q", title="NRW (%)"),
                tooltip=[
                    alt.Tooltip("month_start:T", title="Month"),
                    "nrw_pct:Q",
                    "production_m3:Q",
                    "billed_volume_m3:Q",
                ],
            )
            .properties(height=350)
        )

        st.altair_chart(chart, use_container_width=True)

        with st.expander("Show underlying country-level data"):
            st.dataframe(country_data, use_container_width=True)

    # -------- TAB 2: PRODUCTION vs CONSUMPTION --------
    with tab_prodcons:
        st.subheader("Monthly Production vs Billed Consumption")

        pc_df = country_data[["month_start", "production_m3", "billed_volume_m3"]].copy()
        pc_df = pc_df.melt(
            id_vars="month_start",
            value_vars=["production_m3", "billed_volume_m3"],
            var_name="metric",
            value_name="value",
        )

        metric_labels = {
            "production_m3": "Production (m³)",
            "billed_volume_m3": "Consumption (Billed m³)",
        }
        pc_df["metric_label"] = pc_df["metric"].map(metric_labels)

        options = list(metric_labels.values())
        selected_metrics = st.multiselect(
            "Select series to display",
            options=options,
            default=options,
        )

        if not selected_metrics:
            st.info("Please select at least one series to display.")
        else:
            pc_filtered = pc_df[pc_df["metric_label"].isin(selected_metrics)]

            chart_pc = (
                alt.Chart(pc_filtered)
                .mark_line(point=True)
                .encode(
                    x=alt.X(
                        "month_start:T",
                        title="Month",
                        axis=alt.Axis(format="%b %Y", labelAngle=-45),
                    ),
                    y=alt.Y("value:Q", title="Volume (m³)"),
                    color=alt.Color("metric_label:N", title="Series"),
                    tooltip=[
                        alt.Tooltip("month_start:T", title="Month"),
                        "metric_label:N",
                        alt.Tooltip("value:Q", title="Volume (m³)", format=",.0f"),
                    ],
                )
                .properties(height=350)
            )

            st.altair_chart(chart_pc, use_container_width=True)

            with st.expander("Show underlying production vs consumption data"):
                show_df = country_data[
                    ["month_start", "production_m3", "billed_volume_m3"]
                ].copy()
                st.dataframe(show_df, use_container_width=True)

    # -------- TAB 3: FORECAST: CONSUMPTION --------
    with tab_forecast:
        st.subheader("Forecasted Billed Consumption")

        forecast_horizon = st.slider(
            "Forecast horizon (months)",
            min_value=6,
            max_value=36,
            value=12,
            step=3,
        )

        forecast_df = get_consumption_forecast(selected_country, forecast_horizon)

        # Historical actuals
        hist = country_data[["month_start", "billed_volume_m3"]].rename(
            columns={"month_start": "ds", "billed_volume_m3": "y"}
        )
        hist["type"] = "Actual"

        last_hist_date = hist["ds"].max()

        # Future forecasts only
        future = forecast_df[forecast_df["ds"] > last_hist_date].copy()
        future = future.rename(columns={"yhat": "y"})
        future["type"] = "Forecast"

        plot_df = pd.concat(
            [
                hist[["ds", "y", "type"]],
                future[["ds", "y", "type"]],
            ],
            ignore_index=True,
        )

        chart_fc = (
            alt.Chart(plot_df)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "ds:T",
                    title="Month",
                    axis=alt.Axis(format="%b %Y", labelAngle=-45),
                ),
                y=alt.Y("y:Q", title="Billed Volume (m³)"),
                color=alt.Color("type:N", title="Series"),
                tooltip=[
                    alt.Tooltip("ds:T", title="Month"),
                    "type:N",
                    alt.Tooltip("y:Q", title="Volume (m³)", format=",.0f"),
                ],
            )
            .properties(height=350)
        )

        st.altair_chart(chart_fc, use_container_width=True)

        st.markdown("### Smoothed Consumption Trend (Actuals Only)")
        trend_df = country_data[["month_start", "billed_volume_m3"]].copy()
        trend_df["cons_3m"] = trend_df["billed_volume_m3"].rolling(3).mean()
        trend_df["cons_12m"] = trend_df["billed_volume_m3"].rolling(12).mean()

        trend_long = trend_df.melt(
            id_vars="month_start",
            value_vars=["billed_volume_m3", "cons_3m", "cons_12m"],
            var_name="series",
            value_name="value",
        )

        series_labels = {
            "billed_volume_m3": "Monthly actual",
            "cons_3m": "3-month avg",
            "cons_12m": "12-month avg",
        }
        trend_long["series_label"] = trend_long["series"].map(series_labels)

        chart_trend = (
            alt.Chart(trend_long.dropna())
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "month_start:T",
                    title="Month",
                    axis=alt.Axis(format="%b %Y", labelAngle=-45),
                ),
                y=alt.Y("value:Q", title="Billed Volume (m³)"),
                color=alt.Color("series_label:N", title="Series"),
                tooltip=[
                    alt.Tooltip("month_start:T", title="Month"),
                    "series_label:N",
                    alt.Tooltip("value:Q", title="Volume (m³)", format=",.0f"),
                ],
            )
            .properties(height=300)
        )

        st.altair_chart(chart_trend, use_container_width=True)

        st.markdown("### Seasonal Consumption Pattern (Average by Month)")
        season_df = country_data.copy()
        season_df["month_name"] = season_df["month_start"].dt.strftime("%b")

        month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        chart_season = (
            alt.Chart(season_df)
            .mark_bar()
            .encode(
                x=alt.X("month_name:N", title="Month", sort=month_order),
                y=alt.Y(
                    "billed_volume_m3:Q",
                    aggregate="mean",
                    title="Avg Billed Volume (m³)",
                ),
                tooltip=[
                    "month_name:N",
                    alt.Tooltip(
                        "billed_volume_m3:Q",
                        aggregate="mean",
                        title="Avg Volume (m³)",
                        format=",.0f",
                    ),
                ],
            )
            .properties(height=300)
        )

        st.altair_chart(chart_season, use_container_width=True)

        with st.expander("Show forecast raw data"):
            st.dataframe(future, use_container_width=True)

    # -------- TAB 4: ZONE BILLED VOLUME --------
    with tab_zone_volume:
        st.subheader("Monthly Billed Volume by Zone")

        if zone_data.empty:
            st.info("No zone-level billing data available for this country.")
        else:
            zones = sorted(zone_data["zone"].unique())
            selected_zones = st.multiselect(
                "Select Zones",
                zones,
                default=zones,
            )

            if not selected_zones:
                st.info("Please select at least one zone to display.")
            else:
                zf = zone_data[zone_data["zone"].isin(selected_zones)]

                chart_zone_vol = (
                    alt.Chart(zf)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X(
                            "month_start:T",
                            title="Month",
                            axis=alt.Axis(format="%b %Y", labelAngle=-45),
                        ),
                        y=alt.Y("billed_volume_m3:Q", title="Billed Volume (m³)"),
                        color=alt.Color("zone:N", title="Zone"),
                        tooltip=[
                            alt.Tooltip("month_start:T", title="Month"),
                            "zone:N",
                            "billed_volume_m3:Q",
                        ],
                    )
                    .properties(height=350)
                )

                st.altair_chart(chart_zone_vol, use_container_width=True)

                with st.expander("Show underlying zone-level billed volume data"):
                    st.dataframe(zf, use_container_width=True)

    # -------- TAB 5: ZONE REVENUE & COLLECTIONS --------
    with tab_zone_revenue:
        st.subheader("Zone Revenue & Collection Rates")

        if zone_data.empty:
            st.info("No zone-level billing data available for this country.")
        else:
            zd = zone_data.copy()
            zd["collection_rate"] = zd.apply(
                lambda row: row["paid_amount"] / row["billed_amount"]
                if row["billed_amount"] > 0
                else None,
                axis=1,
            )

            zones = sorted(zd["zone"].unique())
            selected_zones = st.multiselect(
                "Select Zones",
                zones,
                default=zones,
                key="zones_revenue",
            )

            if not selected_zones:
                st.info("Please select at least one zone to display.")
            else:
                zd_sel = zd[zd["zone"].isin(selected_zones)]

                st.markdown("**Collection Rate Over Time**")
                chart_coll = (
                    alt.Chart(zd_sel)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X(
                            "month_start:T",
                            title="Month",
                            axis=alt.Axis(format="%b %Y", labelAngle=-45),
                        ),
                        y=alt.Y(
                            "collection_rate:Q",
                            title="Collection Rate",
                            axis=alt.Axis(format="%", tickCount=5),
                        ),
                        color=alt.Color("zone:N", title="Zone"),
                        tooltip=[
                            alt.Tooltip("month_start:T", title="Month"),
                            "zone:N",
                            alt.Tooltip(
                                "collection_rate:Q",
                                title="Collection Rate",
                                format=".1%",
                            ),
                            "billed_amount:Q",
                            "paid_amount:Q",
                        ],
                    )
                    .properties(height=300)
                )

                st.altair_chart(chart_coll, use_container_width=True)

                st.markdown("### Latest Month Revenue & Collections by Zone")
                latest_month = zd_sel["month_start"].max()
                latest_zd = zd_sel[zd_sel["month_start"] == latest_month].copy()

                latest_zd = latest_zd[
                    ["zone", "billed_amount", "paid_amount", "collection_rate"]
                ].sort_values("collection_rate", ascending=True)

                st.dataframe(latest_zd, use_container_width=True)

    # -------- TAB 6: ZONE CONSUMPTION MIX --------
    with tab_zone_mix:
        st.subheader("Zone Consumption Mix (Billed Volume Share)")

        if zone_data.empty:
            st.info("No zone-level billing data available for this country.")
        else:
            months = sorted(zone_data["month_start"].unique())
            if not months:
                st.info("No monthly data available.")
            else:
                month_labels = [pd.to_datetime(m).strftime("%b %Y") for m in months]
                default_idx = len(months) - 1

                selected_label = st.selectbox(
                    "Select Month",
                    options=month_labels,
                    index=default_idx,
                )
                selected_month = months[month_labels.index(selected_label)]

                mix_df = zone_data[zone_data["month_start"] == selected_month].copy()

                total_vol = mix_df["billed_volume_m3"].sum()
                if total_vol > 0:
                    mix_df["volume_share"] = mix_df["billed_volume_m3"] / total_vol
                else:
                    mix_df["volume_share"] = 0.0

                st.markdown(f"**Zone share of billed volume for {selected_label}**")

                chart_mix = (
                    alt.Chart(mix_df)
                    .mark_bar()
                    .encode(
                        x=alt.X("zone:N", title="Zone"),
                        y=alt.Y(
                            "volume_share:Q",
                            title="Share of Billed Volume",
                            axis=alt.Axis(format="%", tickCount=5),
                        ),
                        tooltip=[
                            "zone:N",
                            "billed_volume_m3:Q",
                            alt.Tooltip("volume_share:Q", title="Share", format=".1%"),
                        ],
                    )
                    .properties(height=350)
                )

                st.altair_chart(chart_mix, use_container_width=True)

                with st.expander("Show underlying mix data"):
                    st.dataframe(
                        mix_df[["zone", "billed_volume_m3", "volume_share"]],
                        use_container_width=True,
                    )
