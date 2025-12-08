# preprocessing/preprocess_data.py

import os
from glob import glob
from typing import Literal

import pandas as pd

# Path to the data directory, relative to repo root
#DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
## Path to the data directory, relative to repo root
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "production_operations_data")


# ---------- 1. RAW LOADERS ----------

def load_billing() -> pd.DataFrame:
    """
    Load and concatenate all billing_*.csv files from the data directory.
    Adds year, month, and month_start columns.
    """
    pattern = os.path.join(DATA_DIR, "billing_*.csv")
    files = glob(pattern)

    if not files:
        raise FileNotFoundError(f"No billing_*.csv files found in {DATA_DIR}")

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        df["date"] = pd.to_datetime(df["date"])
        dfs.append(df)

    billing = pd.concat(dfs, ignore_index=True)

    billing["year"] = billing["date"].dt.year
    billing["month"] = billing["date"].dt.month
    billing["month_start"] = billing["date"].dt.to_period("M").dt.to_timestamp()

    return billing


def load_production() -> pd.DataFrame:
    """
    Load and concatenate all production_*.csv files from the data directory.
    Adds year, month, and month_start columns.
    """
    pattern = os.path.join(DATA_DIR, "production_*.csv")
    files = glob(pattern)

    if not files:
        raise FileNotFoundError(f"No production_*.csv files found in {DATA_DIR}")

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        df["date"] = pd.to_datetime(df["date"])
        dfs.append(df)

    production = pd.concat(dfs, ignore_index=True)

    production["year"] = production["date"].dt.year
    production["month"] = production["date"].dt.month
    production["month_start"] = production["date"].dt.to_period("M").dt.to_timestamp()

    return production


# ---------- 2. MONTHLY AGGREGATORS ----------

def monthly_production_by(level: Literal["country"] = "country") -> pd.DataFrame:
    """
    Monthly aggregated production.
    Currently supports only country-level aggregation.
    """
    prod = load_production()

    if level == "country":
        group_cols = ["country", "year", "month", "month_start"]
    else:
        raise ValueError(f"Unsupported production level: {level}")

    agg = (
        prod.groupby(group_cols, as_index=False)
        .agg(
            production_m3=("production_m3", "sum"),
            avg_service_hours=("service_hours", "mean"),
        )
    )
    return agg


def monthly_billing_by(
    level: Literal["country", "country_zone"] = "country",
) -> pd.DataFrame:
    """
    Monthly aggregated billing.

    level="country":
        groups by [country, year, month, month_start]
    level="country_zone":
        groups by [country, zone, year, month, month_start]
    """
    bill = load_billing()

    if level == "country":
        group_cols = ["country", "year", "month", "month_start"]
    elif level == "country_zone":
        group_cols = ["country", "zone", "year", "month", "month_start"]
    else:
        raise ValueError(f"Unsupported billing level: {level}")

    agg = (
        bill.groupby(group_cols, as_index=False)
        .agg(
            billed_volume_m3=("consumption_m3", "sum"),
            billed_amount=("billed", "sum"),
            paid_amount=("paid", "sum"),
        )
    )
    return agg


# ---------- 3. NRW METRICS (COUNTRY LEVEL) ----------

def monthly_nrw_country() -> pd.DataFrame:
    """
    Monthly country-level NRW%.

    NRW% = ((production_m3 - billed_volume_m3) / production_m3) * 100
    """
    prod_m = monthly_production_by("country")
    bill_m = monthly_billing_by("country")

    df = prod_m.merge(
        bill_m,
        on=["country", "year", "month", "month_start"],
        how="inner",
        validate="one_to_one",
    )

    # Avoid division by zero
    df = df[df["production_m3"] > 0].copy()

    df["nrw_pct"] = (
        (df["production_m3"] - df["billed_volume_m3"]) / df["production_m3"]
    ) * 100

    return df

