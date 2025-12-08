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

    if df_country.empty:
        return pd.DataFrame(columns=["ds", "yhat", "yhat_lower", "yhat_upper"])

    # Prepare data for Prophet
    df = df_country[["month_start", "billed_volume_m3"]].rename(
        columns={"month_start": "ds", "billed_volume_m3": "y"}
    )

    model = Prophet()
    model.fit(df)

    future = model.make_future_dataframe(periods=periods, freq="MS")
    forecast = model.predict(future)

    return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]


@st.cache_data
def get_in_sample_fit(country: str) -> pd.DataFrame:
    """
    Fit Prophet on the full history for the selected country and return
    ds, actual, predicted, error and abs_error for each historical month.
    """
    df_country = prep.monthly_nrw_country()
    df_country = df_country[df_country["country"] == country].copy()
    df_country = df_country.sort_values("month_start")

    if df_country.empty:
        return pd.DataFrame(columns=["ds", "actual", "predicted", "error", "abs_error"])

    df = df_country[["month_start", "billed_volume_m3"]].rename(
        columns={"month_start": "ds", "billed_volume_m3": "y"}
    )

    model = Prophet()
    model.fit(df)

    forecast = model.predict(df[["ds"]])

    merged = df.merge(forecast[["ds", "yhat"]], on="ds", how="left")
    merged["actual"] = merged["y"]
    merged["predicted"] = merged["yhat"]
    merged["error"] = merged["predicted"] - merged["actual"]
    merged["abs_error"] = merged["error"].abs()

    return merged[["ds", "actual", "predicted", "error", "abs_error"]]


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
    country_data["production_3m_avg"] = (
        country_data["production_m3"].rolling(3).mean()
    )
    country_data["consumption_3m_avg"] = (
        country_data["billed_volume_m3"].rolling(3).mean()
    )
    country_data["consumption_12m_avg"] = (
        country_data["billed_volume_m3"].rolling(12).mean()
    )

    # -------- Simple NRW anomaly flags --------
    # Domain sanity check: NRW should normally be between 0 and 100%
    country_data["nrw_sanity_anomaly"] = (
        country_data["nrw_pct"] < 0
    ) | (country_data["nrw_pct"] > 100)

    # OPTIONAL: simple statistical anomaly vs 12-month rolling median
    country_data["nrw_roll_median"] = country_data["nrw_pct"].rolling(12).median()
    country_data["nrw_abs_dev"] = (
        country_data["nrw_pct"] - country_data["nrw_roll_median"]
    ).abs()

    dev_median = country_data["nrw_abs_dev"].median()
    if pd.notna(dev_median) and dev_median > 0:
        threshold = 3 * dev_median
        country_data["nrw_stat_anomaly"] = country_data["nrw_abs_dev"] > threshold
    else:
        country_data["nrw_stat_anomaly"] = False

    country_data["nrw_anomaly"] = (
        country_data["nrw_sanity_anomaly"] | country_data["nrw_stat_anomaly"]
    )

    # Latest / previous rows (now that all columns exist)
    latest = country_data.iloc[-1]
    prev = country_data.iloc[-2] if len(country_data) > 1 else None

    # If the latest NRW is anomalous, show a global banner on the page
    if bool(latest.get("nrw_anomaly", False)):
        st.warning(
            "⚠️ The latest NRW value looks unusual (for example below 0% or above 100%). "
            "Please check the underlying production and billing data for this period."
        )

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
        delta_pct = nrw_yoy  # numeric delta for coloring

        if delta_pct is None:
            st.metric(
                label=f"NRW (%) – {selected_country}",
                value=f"{nrw_value:.1f}%",
            )
        else:
            st.metric(
                label=f"NRW (%) – {selected_country}",
                value=f"{nrw_value:.1f}%",
                delta=f"{delta_pct:+.1f} pp vs last year",
                delta_color="inverse",  # lower NRW = green, higher NRW = red
            )

        nrw_3m = latest["nrw_3m_avg"]
        if pd.notna(nrw_3m):
            st.caption(f"3-month avg NRW: {nrw_3m:.1f}%")

        # Add anomaly note inside the KPI card if applicable
        if latest.get("nrw_anomaly", False):
            st.markdown(
                "<span style='color:#FF6B6B; font-size:0.9rem;'>"
                "⚠️ This month's NRW value appears unusual and may require data review."
                "</span>",
                unsafe_allow_html=True,
            )

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

    (
        tab_nrw,
        tab_prodcons,
        tab_forecast,
        tab_nrw_finance,
        tab_continuity,
        tab_zone_mix,
        tab_zone_volume,
        tab_zone_revenue,
    ) = st.tabs(
        [
            "NRW Overview",
            "Production vs Consumption",
            "Forecast: Consumption",
            "NRW – Financial Impact",
            "Continuity of Supply",
            "Zone Consumption Mix",
            "Zone Billed Volume",
            "Zone Revenue & Collections",
        ]
    )

    # -------- TAB 1: NRW OVERVIEW (COUNTRY) --------
    with tab_nrw:
        st.subheader("Monthly NRW% (Country Level)")

        base = alt.Chart(country_data).encode(
            x=alt.X(
                "month_start:T",
                title="Month",
                axis=alt.Axis(format="%b %Y", labelAngle=-45),
            ),
            y=alt.Y(
                "nrw_pct:Q",
                title="NRW (%)",
                scale=alt.Scale(zero=False),  # no forced zero, less blank space
            ),
            tooltip=[
                alt.Tooltip("month_start:T", title="Month"),
                "nrw_pct:Q",
                "production_m3:Q",
                "billed_volume_m3:Q",
            ],
        )

        line = base.mark_line()

        pts = base.mark_circle(size=70).encode(
            color=alt.condition(
                alt.datum.nrw_anomaly,
                alt.value("#FF4B4B"),  # anomaly: red
                alt.value("#4BC0C0"),  # normal: teal-ish
            ),
        )

        st.altair_chart((line + pts).interactive(), use_container_width=True)

        st.caption(
            "Red points indicate months where NRW looks unusual (for example below 0% "
            "or above 100%) or far from the typical pattern. These months may need "
            "a data quality review."
        )

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

        # ---- Model fit vs actual over the full history ----
        st.markdown("### How well does the model follow past consumption?")

        fit_df = get_in_sample_fit(selected_country)

        if fit_df.empty:
            st.info("Not enough data to show model fit.")
        else:
            fit_long = fit_df.melt(
                id_vars="ds",
                value_vars=["actual", "predicted"],
                var_name="series",
                value_name="value",
            )

            series_labels = {
                "actual": "Actual billed consumption",
                "predicted": "Model fit",
            }
            fit_long["series_label"] = fit_long["series"].map(series_labels)

            chart_fit = (
                alt.Chart(fit_long)
                .mark_line(point=True)
                .encode(
                    x=alt.X(
                        "ds:T",
                        title="Month",
                        axis=alt.Axis(format="%b %Y", labelAngle=-45),
                    ),
                    y=alt.Y(
                        "value:Q",
                        title="Billed Volume (m³)",
                        scale=alt.Scale(zero=False),
                    ),
                    color=alt.Color("series_label:N", title="Series"),
                    tooltip=[
                        alt.Tooltip("ds:T", title="Month"),
                        "series_label:N",
                        alt.Tooltip("value:Q", title="Volume (m³)", format=",.0f"),
                    ],
                )
                .properties(height=300)
                .interactive()
            )

            st.altair_chart(chart_fit, use_container_width=True)

            st.caption(
                "Blue line = actual billed consumption. "
                "Teal line = what the model would have predicted for those same months."
            )

            st.markdown("#### Difference between model and actual (per month)")

            error_chart = (
                alt.Chart(fit_df)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "ds:T",
                        title="Month",
                        axis=alt.Axis(format="%b %Y", labelAngle=-45),
                    ),
                    y=alt.Y(
                        "abs_error:Q",
                        title="Absolute difference (m³)",
                        scale=alt.Scale(zero=False),
                    ),
                    tooltip=[
                        alt.Tooltip("ds:T", title="Month"),
                        alt.Tooltip(
                            "abs_error:Q",
                            title="Difference between model and actual (m³)",
                            format=",.0f",
                        ),
                    ],
                )
                .properties(height=200)
                .interactive()
            )

            st.altair_chart(error_chart, use_container_width=True)

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

        month_order = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]

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

    # -------- TAB 7: CONTINUITY OF SUPPLY --------
    with tab_continuity:
        st.subheader("Continuity of Water Supply (Hours per Day)")

        if "avg_service_hours" not in country_data.columns:
            st.info("Service hours are not available in the aggregated dataset.")
        else:
            latest_hours = latest["avg_service_hours"]
            last_12m = country_data.tail(12)["avg_service_hours"]
            avg_12m = last_12m.mean() if len(last_12m) > 0 else None

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.metric(
                    "Latest average supply (hours/day)",
                    f"{latest_hours:.1f} h/day",
                )
            with col_c2:
                if avg_12m is not None:
                    st.metric(
                        "12-month average supply",
                        f"{avg_12m:.1f} h/day",
                    )

            chart_hours = (
                alt.Chart(country_data)
                .mark_line(point=True)
                .encode(
                    x=alt.X(
                        "month_start:T",
                        title="Month",
                        axis=alt.Axis(format="%b %Y", labelAngle=-45),
                    ),
                    y=alt.Y(
                        "avg_service_hours:Q",
                        title="Average service hours per day",
                    ),
                    tooltip=[
                        alt.Tooltip("month_start:T", title="Month"),
                        alt.Tooltip(
                            "avg_service_hours:Q", title="Hours/day", format=".1f"
                        ),
                    ],
                )
                .properties(height=350)
            )

            st.altair_chart(chart_hours, use_container_width=True)

            st.markdown("### Relationship between Service Hours and Consumption")

            scatter = (
                alt.Chart(country_data)
                .mark_circle(size=80)
                .encode(
                    x=alt.X(
                        "avg_service_hours:Q",
                        title="Average service hours per day",
                    ),
                    y=alt.Y(
                        "billed_volume_m3:Q",
                        title="Billed volume (m³)",
                    ),
                    color=alt.Color("year:O", title="Year"),
                    tooltip=[
                        alt.Tooltip("month_start:T", title="Month"),
                        "avg_service_hours:Q",
                        "billed_volume_m3:Q",
                        "year:O",
                    ],
                )
                .properties(height=350)
            )

            st.altair_chart(scatter, use_container_width=True)

            with st.expander("Show underlying continuity data"):
                st.dataframe(
                    country_data[
                        ["month_start", "avg_service_hours", "billed_volume_m3"]
                    ],
                    use_container_width=True,
                )

    # -------- TAB 8: NRW – FINANCIAL IMPACT --------
    with tab_nrw_finance:
        st.subheader("Financial Impact of Non-Revenue Water")

        needed_cols = {"production_m3", "billed_volume_m3", "billed_amount"}
        if not needed_cols.issubset(set(country_data.columns)):
            st.info(
                "Cannot compute financial impact of NRW: required fields are missing "
                "(production_m3, billed_volume_m3, billed_amount)."
            )
        else:
            df_fin = country_data.copy()

            df_fin["nrw_volume_m3"] = (
                df_fin["production_m3"] - df_fin["billed_volume_m3"]
            )

            df_fin["implied_tariff"] = df_fin.apply(
                lambda row: row["billed_amount"] / row["billed_volume_m3"]
                if row["billed_volume_m3"] > 0
                else None,
                axis=1,
            )

            df_fin["nrw_revenue_equiv"] = df_fin.apply(
                lambda row: row["nrw_volume_m3"] * row["implied_tariff"]
                if pd.notna(row["implied_tariff"]) and row["nrw_volume_m3"] > 0
                else 0.0,
                axis=1,
            )

            last_12 = df_fin.tail(12)
            total_nrw_rev_12m = last_12["nrw_revenue_equiv"].sum()
            total_billed_12m = last_12["billed_amount"].sum()
            nrw_rev_share_12m = (
                total_nrw_rev_12m / total_billed_12m * 100
                if total_billed_12m > 0
                else None
            )

            k1, k2 = st.columns(2)
            with k1:
                st.metric(
                    "Estimated NRW-related revenue at risk (last 12 months)",
                    f"{total_nrw_rev_12m:,.0f}",
                    help=(
                        "Approximate value of water produced but not billed, "
                        "valued at the average tariff."
                    ),
                )
            with k2:
                if nrw_rev_share_12m is not None:
                    st.metric(
                        "NRW as % of billed revenue (last 12 months)",
                        f"{nrw_rev_share_12m:.1f}%",
                    )
                else:
                    st.metric(
                        "NRW as % of billed revenue (last 12 months)",
                        "N/A",
                    )

            st.markdown("### Monthly Estimated Revenue at Risk from NRW")

            chart_nrw_rev = (
                alt.Chart(df_fin)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "month_start:T",
                        title="Month",
                        axis=alt.Axis(format="%b %Y", labelAngle=-45),
                    ),
                    y=alt.Y(
                        "nrw_revenue_equiv:Q",
                        title="Estimated NRW-related revenue (currency units)",
                    ),
                    tooltip=[
                        alt.Tooltip("month_start:T", title="Month"),
                        alt.Tooltip(
                            "nrw_revenue_equiv:Q",
                            title="NRW revenue equivalent",
                            format=",.0f",
                        ),
                        alt.Tooltip(
                            "nrw_volume_m3:Q", title="NRW volume (m³)", format=",.0f"
                        ),
                        alt.Tooltip(
                            "implied_tariff:Q", title="Implied tariff", format=",.2f"
                        ),
                    ],
                )
                .properties(height=350)
            )

            st.altair_chart(chart_nrw_rev, use_container_width=True)

            st.markdown("### NRW% vs Revenue Impact")

            chart_nrw_pct = (
                alt.Chart(df_fin)
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
                    ],
                )
                .properties(height=250)
            )

            st.altair_chart(chart_nrw_pct, use_container_width=True)

            with st.expander("Show underlying NRW financial data"):
                st.dataframe(
                    df_fin[
                        [
                            "month_start",
                            "production_m3",
                            "billed_volume_m3",
                            "billed_amount",
                            "nrw_volume_m3",
                            "implied_tariff",
                            "nrw_revenue_equiv",
                            "nrw_pct",
                        ]
                    ],
                    use_container_width=True,
                )
