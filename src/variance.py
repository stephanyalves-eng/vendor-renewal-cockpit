"""Budget-vs-actual variance split into price, volume and unbudgeted spend.

    total variance = (P_actual - P_budget) x Q_actual    price
                   + (Q_actual - Q_budget) x P_budget    volume
                   + spend with no budget line           unbudgeted

Q is the billed quantity (seats, usage units, or 1 for a fixed fee), so the split answers the
business question "did we pay more per unit, buy more units, or buy something nobody planned?".

Amounts are handled in integer centavos. Volume is rounded to the cent and price is what remains
of the total, so price + volume + unbudgeted equals the total exactly. The price figure then
differs from the textbook formula by less than one cent per vendor-month.

Two scopes are produced:
* ytd        - closed months of the fiscal year (actuals) vs. the budget for the same months.
* fy_landing - actuals to date plus the forecast for the rest of the year vs. the full-year budget.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

KEY = ["month", "vendor_id"]


def _cents(s: pd.Series) -> pd.Series:
    return (s.astype(float) * 100).round().astype("int64")


def decompose(actual: pd.DataFrame, budget: pd.DataFrame) -> pd.DataFrame:
    """actual: month, vendor_id, actual_qty, actual_amount.
    budget: month, vendor_id, budget_qty, budget_unit_price, budget_amount."""
    df = actual[KEY + ["actual_qty", "actual_amount"]].merge(
        budget[KEY + ["budget_qty", "budget_unit_price", "budget_amount"]], on=KEY, how="outer")
    budgeted = df["budget_amount"].notna()
    df["actual_qty"] = df["actual_qty"].fillna(0.0)
    df["actual_amount"] = df["actual_amount"].fillna(0.0)
    df["budget_amount"] = df["budget_amount"].fillna(0.0)

    a_c, b_c = _cents(df["actual_amount"]), _cents(df["budget_amount"])
    vol_c = pd.Series(0, index=df.index, dtype="int64")
    vol_c[budgeted] = _cents((df.loc[budgeted, "actual_qty"] - df.loc[budgeted, "budget_qty"])
                             * df.loc[budgeted, "budget_unit_price"])
    unb_c = np.where(budgeted, 0, a_c)
    price_c = np.where(budgeted, a_c - b_c - vol_c, 0)

    df["total_var"] = (a_c - b_c) / 100
    df["price_var"] = price_c / 100
    df["volume_var"] = vol_c / 100
    df["unbudgeted_var"] = unb_c / 100
    df["actual_unit_price"] = np.where(df["actual_qty"] > 0, df["actual_amount"] / df["actual_qty"].where(df["actual_qty"] > 0), np.nan)
    return df.sort_values(KEY).reset_index(drop=True)


def variance(data: dict, fc: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    fy = cfg["scenario"]["fiscal_year"]
    spend = data["monthly_spend"]
    budget = data["budget"][data["budget"]["month"].dt.year == fy]

    actual = spend[spend["month"].dt.year == fy].rename(columns={"billed_qty": "actual_qty"})
    actual = actual.groupby(KEY, as_index=False)[["actual_qty", "actual_amount"]].sum()
    closed = budget[budget["month"] <= pd.Timestamp(cfg["scenario"]["history_end"])]
    ytd = decompose(actual, closed).assign(scope="ytd")

    future = fc[fc["month"].dt.year == fy].rename(columns={"forecast_qty": "actual_qty",
                                                           "forecast_amount": "actual_amount"})
    future = future.groupby(KEY, as_index=False)[["actual_qty", "actual_amount"]].sum()
    landing = decompose(pd.concat([actual, future], ignore_index=True), budget).assign(scope="fy_landing")

    out = pd.concat([ytd, landing], ignore_index=True)
    out = out.merge(data["vendors"][["vendor_id", "category", "owner_department"]], on="vendor_id", how="left")
    out.insert(0, "fiscal_year", fy)
    cols = ["fiscal_year", "scope", "month", "vendor_id", "category", "owner_department",
            "actual_qty", "actual_unit_price", "actual_amount", "budget_qty", "budget_unit_price",
            "budget_amount", "price_var", "volume_var", "unbudgeted_var", "total_var"]
    return out[cols]


def waterfall(var: pd.DataFrame, scope: str = "fy_landing") -> pd.DataFrame:
    v = var[var["scope"] == scope]
    budget = v["budget_amount"].sum()
    steps = [("budget", budget), ("price", v["price_var"].sum()), ("volume", v["volume_var"].sum()),
             ("unbudgeted", v["unbudgeted_var"].sum()), ("landing", v["actual_amount"].sum())]
    return pd.DataFrame(steps, columns=["step", "amount"]).round(2)
