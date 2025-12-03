# modules/access.py

import streamlit as st
import pandas as pd
import altair as alt


@st.cache_data
def load_access_data():
    """Load and clean water & sanitation access data."""
    water = pd.read_csv("data/water_access.csv")
    san = pd.read_csv("data/s_access.csv")

    # Normalise country names and create a numeric year column
    for df in (water, san):
        if "country" in df.columns:
            df["country"] = df["country"].astype(str).str.title()

        df["date_YY"] = pd.to_datetime(df["date_YY"], format="%Y")
        df["year"] = df["date_YY"].dt.year

    return water, san


def render_access_page(selected_countries, year_range):
    """
    Access to Water & Sanitation page.

    Parameters
    ----------
    selected_countries : list or None
        From global sidebar multiselect in app.py
    year_range : (int, int)
        From global sidebar year-range slider in app.py
    """

    st.title("Access to Water & Sanitation")

    water, san = load_access_data()

    # ----------------------------------------------------
    # Apply GLOBAL filters: country (can be multi) & year range
    # ----------------------------------------------------
    if selected_countries:
        water = water[water["country"].isin(selected_countries)]
        san = san[san["country"].isin(selected_countries)]

    start_year, end_year = year_range
    water = water[(water["year"] >= start_year) & (water["year"] <= end_year)]
    san = san[(san["year"] >= start_year) & (san["year"] <= end_year)]

    if water.empty or san.empty:
        st.warning("No access data for the current global filters.")
        return

    # For cross-sectional views, use the latest year in the selected range
    current_year = end_year
    w_year = water[water["year"] == current_year].copy()
    s_year = san[san["year"] == current_year].copy()

    if w_year.empty or s_year.empty:
        st.warning(f"No access data for year {current_year}. Try expanding the year range.")
        return

    # ----------------------------------------------------
    # LOCAL filter: Zones
    # (we keep country from global filters, but show combined label for clarity)
    # ----------------------------------------------------
    w_year["country_zone"] = w_year["country"] + " – " + w_year["zone"]
    s_year["country_zone"] = s_year["country"] + " – " + s_year["zone"]


    zone_labels = sorted(w_year["country_zone"].unique())

    selected_zone_labels = st.multiselect(
        "Zones (within selected country/year filters)",
        options=zone_labels,
        default=zone_labels,
        help="Filter to specific zones. If you clear this, all zones in the filtered data will be used.",
    )

    if not selected_zone_labels:
        selected_zone_labels = zone_labels

    w_year_zone = w_year[w_year["country_zone"].isin(selected_zone_labels)]
    s_year_zone = s_year[s_year["country_zone"].isin(selected_zone_labels)]

    # ----------------------------------------------------
    # Helper: population-weighted percentage
    # ----------------------------------------------------
    def pop_weighted_pct(df: pd.DataFrame, pct_col: str) -> float:
        """Population-weighted average of a percentage column."""
        if df.empty or "popn_total" not in df.columns:
            return 0.0
        total_pop = df["popn_total"].sum()
        if total_pop == 0:
            return 0.0
        return float((df[pct_col] * df["popn_total"]).sum() / total_pop)

    # ----------------------------------------------------
    # Tabs to keep layout organised
    # ----------------------------------------------------
    tab_overview, tab_gaps, tab_trends = st.tabs(
        ["Overview", "Gaps & Priorities", "Trends"]
    )

    # ====================================================
    # TAB 1: OVERVIEW
    # ====================================================
    with tab_overview:
        st.markdown(f"### Overview for **{current_year}**")

        # ---------- KPIs ----------
        kpi_cols = st.columns(4)

        water_safe_pct = pop_weighted_pct(w_year_zone, "safely_managed_pct")
        san_safe_pct = pop_weighted_pct(s_year_zone, "safely_managed_pct")

        # “No basic water” = limited + unimproved + surface water
        no_basic_water_pct = (
            pop_weighted_pct(w_year_zone, "limited_pct")
            + pop_weighted_pct(w_year_zone, "unimproved_pct")
            + pop_weighted_pct(w_year_zone, "surface_water_pct")
        )

        open_def_pct = pop_weighted_pct(s_year_zone, "open_def_pct")

        with kpi_cols[0]:
            st.metric("Safely managed water (%)", f"{water_safe_pct:0.1f}")
        with kpi_cols[1]:
            st.metric("Safely managed sanitation (%)", f"{san_safe_pct:0.1f}")
        with kpi_cols[2]:
            st.metric("Population without basic water (%)", f"{no_basic_water_pct:0.1f}")
        with kpi_cols[3]:
            st.metric("Open defecation (%)", f"{open_def_pct:0.1f}")

        st.markdown(
            "_KPIs are population-weighted across the selected zones and countries._"
        )

        # ---------- Water service ladder ----------
        st.subheader("Water service ladder by zone")

        if not w_year_zone.empty:
            ladder_map_w = {
                "Safely managed": "safely_managed_pct",
                "Basic": "basic_pct",
                "Limited": "limited_pct",
                "Unimproved": "unimproved_pct",
                "Surface water": "surface_water_pct",
            }

            water_long = w_year_zone.melt(
                id_vars=["country", "zone", "country_zone"],
                value_vars=list(ladder_map_w.values()),
                var_name="indicator",
                value_name="pct",
            )
            inv_map_w = {v: k for k, v in ladder_map_w.items()}
            water_long["Service level"] = water_long["indicator"].map(inv_map_w)

            chart_water = (
                alt.Chart(water_long)
                .mark_bar()
                .encode(
                    x=alt.X("zone:N", title="Zone"),
                    y=alt.Y("pct:Q", stack="normalize", title="Share of population"),
                    color=alt.Color("Service level:N", title="Service level"),
                    tooltip=[
                        "country",
                        "zone",
                        "Service level",
                        alt.Tooltip("pct:Q", format=".1f"),
                    ],
                )
                .properties(height=350)
            )

            st.altair_chart(chart_water, use_container_width=True)
        else:
            st.info("No water access data for this selection.")

        # ---------- Sanitation service ladder ----------
        st.subheader("Sanitation service ladder by zone")

        if not s_year_zone.empty:
            ladder_map_s = {
                "Safely managed": "safely_managed_pct",
                "Basic": "basic_pct",
                "Limited": "limited_pct",
                "Unimproved": "unimproved_pct",
                "Open defecation": "open_def_pct",
            }

            san_long = s_year_zone.melt(
                id_vars=["country", "zone", "country_zone"],
                value_vars=list(ladder_map_s.values()),
                var_name="indicator",
                value_name="pct",
            )
            inv_map_s = {v: k for k, v in ladder_map_s.items()}
            san_long["Service level"] = san_long["indicator"].map(inv_map_s)

            chart_san = (
                alt.Chart(san_long)
                .mark_bar()
                .encode(
                    x=alt.X("zone:N", title="Zone"),
                    y=alt.Y("pct:Q", stack="normalize", title="Share of population"),
                    color=alt.Color("Service level:N", title="Service level"),
                    tooltip=[
                        "country",
                        "zone",
                        "Service level",
                        alt.Tooltip("pct:Q", format=".1f"),
                    ],
                )
                .properties(height=350)
            )

            st.altair_chart(chart_san, use_container_width=True)
        else:
            st.info("No sanitation access data for this selection.")

    # ====================================================
    # TAB 2: GAPS & PRIORITIES
    # ====================================================
    with tab_gaps:
        st.markdown(f"### Priority zones for {current_year}")

        if w_year_zone.empty:
            st.info("No data available for the selected filters.")
        else:
            # Combine water + sanitation metrics for the same year
            pri = w_year_zone[
                [
                    "country",
                    "zone",
                    "year",
                    "popn_total",
                    "safely_managed_pct",
                    "basic_pct",
                    "limited_pct",
                    "unimproved_pct",
                    "surface_water_pct",
                ]
            ].copy()
            pri = pri.rename(columns={"safely_managed_pct": "safe_water_pct"})

            san_merge = s_year_zone[
                ["country", "zone", "year", "safely_managed_pct", "open_def_pct"]
            ].copy()
            san_merge = san_merge.rename(columns={"safely_managed_pct": "safe_san_pct"})

            pri = pri.merge(san_merge, on=["country", "zone", "year"], how="left")

            pri["no_basic_water_pct"] = (
                pri["limited_pct"]
                + pri["unimproved_pct"]
                + pri["surface_water_pct"]
            )
            pri["water_san_gap_pct"] = pri["safe_water_pct"] - pri["safe_san_pct"]

            # Simple priority score: no-basic water + open defecation
            pri["priority_score"] = pri["no_basic_water_pct"] + pri["open_def_pct"]
            pri_sorted = pri.sort_values("priority_score", ascending=False)

            st.caption(
                "Zones are ranked by a simple priority score combining "
                "**population without basic water** and **open defecation**."
            )

            st.dataframe(
                pri_sorted[
                    [
                        "country",
                        "zone",
                        "popn_total",
                        "no_basic_water_pct",
                        "open_def_pct",
                        "safe_water_pct",
                        "safe_san_pct",
                    ]
                ]
                .rename(
                    columns={
                        "popn_total": "Population",
                        "no_basic_water_pct": "No basic water (%)",
                        "open_def_pct": "Open defecation (%)",
                        "safe_water_pct": "Safely managed water (%)",
                        "safe_san_pct": "Safely managed sanitation (%)",
                    }
                )
                .round(1),
                use_container_width=True,
                height=350,
            )

            st.markdown("#### Gap between water and sanitation (safely managed)")

            gap_chart = (
                alt.Chart(pri)
                .mark_bar()
                .encode(
                    y=alt.Y("zone:N", title="Zone", sort="-x"),
                    x=alt.X(
                        "water_san_gap_pct:Q",
                        title="Water – Sanitation safely managed (percentage points)",
                    ),
                    color=alt.condition(
                        "datum.water_san_gap_pct >= 0",
                        alt.value("#4caf50"),  # water ahead of sanitation
                        alt.value("#f44336"),  # sanitation ahead of water
                    ),
                    tooltip=[
                        "country",
                        "zone",
                        alt.Tooltip(
                            "safe_water_pct:Q",
                            format=".1f",
                            title="Water safely managed (%)",
                        ),
                        alt.Tooltip(
                            "safe_san_pct:Q",
                            format=".1f",
                            title="Sanitation safely managed (%)",
                        ),
                        alt.Tooltip(
                            "water_san_gap_pct:Q", format=".1f", title="Gap (W - S)"
                        ),
                    ],
                )
                .properties(height=350)
            )

            st.altair_chart(gap_chart, use_container_width=True)
            st.caption(
                "Positive values mean water access is ahead of sanitation; "
                "negative values mean sanitation is ahead of water. Large gaps "
                "highlight where services are unbalanced."
            )

    # ====================================================
    # TAB 3: TRENDS
    # ====================================================
    with tab_trends:
        st.markdown("### Trend in safely managed services (water vs sanitation)")

        # Use ALL years in the selected range, but only selected zones
        water_sel = water.copy()
        san_sel = san.copy()

        water_sel["country_zone"] = water_sel["country"] + " – " + water_sel["zone"]
        san_sel["country_zone"] = san_sel["country"] + " – " + san_sel["zone"]

        water_sel = water_sel[water_sel["country_zone"].isin(selected_zone_labels)]
        san_sel = san_sel[san_sel["country_zone"].isin(selected_zone_labels)]

        rows = []
        for y in range(start_year, end_year + 1):
            w_y = water_sel[water_sel["year"] == y]
            s_y = san_sel[san_sel["year"] == y]

            if not w_y.empty:
                rows.append(
                    {
                        "Year": y,
                        "Service": "Water",
                        "Safe_pct": pop_weighted_pct(w_y, "safely_managed_pct"),
                    }
                )
            if not s_y.empty:
                rows.append(
                    {
                        "Year": y,
                        "Service": "Sanitation",
                        "Safe_pct": pop_weighted_pct(s_y, "safely_managed_pct"),
                    }
                )

        trend_df = pd.DataFrame(rows)

        if not trend_df.empty:
            trend_chart = (
                alt.Chart(trend_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X("Year:O"),
                    y=alt.Y("Safe_pct:Q", title="Safely managed (%)"),
                    color=alt.Color("Service:N"),
                    tooltip=[
                        "Year",
                        "Service",
                        alt.Tooltip("Safe_pct:Q", format=".1f"),
                    ],
                )
                .properties(height=350)
            )

            st.altair_chart(trend_chart, use_container_width=True)
            st.caption(
                "Shows overall progress in safely managed water and sanitation "
                "for the selected zones and countries over the chosen time period."
            )
        else:
            st.info("No trend data for the selected filters.")
