"""Forecast spend to the end of the fiscal year and for a rolling 12 months, then compute the
fiscal-year landing (actuals to date + forecast of the remaining months) against budget.

One rule per billing model, chosen because it mirrors how the invoice is actually built:

* per_seat - seats = projected department headcount x observed adoption rate. The vendor bills
  the contracted seats or the active seats, whichever is higher (true-up). The price steps up by
  the contract escalator in the month after the term ends.
* usage    - linear trend over the last N months on seasonally adjusted volumes, multiplied back
  by a calendar-month seasonal index learned from the full history.
* fixed    - annual contract value / 12, stepped up by the escalator after the term ends.

The forecast assumes the status quo: every live contract renews on its current terms. The
savings from recommendations are reported separately, as upside against this baseline.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.generate import COMPANY_WIDE_OWNER, price_at


def horizon_months(cfg: dict) -> list[pd.Timestamp]:
    start = pd.Timestamp(cfg["scenario"]["history_end"]) + pd.DateOffset(months=1)
    return list(pd.date_range(start, periods=cfg["scenario"]["forecast_horizon_months"], freq="MS"))


def _linear_projection(values: np.ndarray, steps_ahead: np.ndarray) -> np.ndarray:
    """Fit y = a + b*t on t = 0..n-1 and evaluate at t = n-1 + steps_ahead."""
    t = np.arange(len(values))
    slope, intercept = np.polyfit(t, values, 1)
    return intercept + slope * (len(values) - 1 + steps_ahead)


def project_headcount(headcount: pd.DataFrame, months: list, trend_months: int) -> pd.DataFrame:
    """Department headcount projected with a linear trend over the last `trend_months` months."""
    wide = headcount.pivot(index="month", columns="department", values="headcount").sort_index()
    steps = np.arange(1, len(months) + 1)
    out = {dept: np.maximum(0, _linear_projection(wide[dept].iloc[-trend_months:].to_numpy(float), steps))
           for dept in wide.columns}
    return pd.DataFrame(out, index=pd.DatetimeIndex(months, name="month"))


def seasonal_index(series: pd.Series) -> pd.Series:
    """Calendar-month index (mean 1) of a monthly series, after removing a linear trend."""
    s = series.sort_index().astype(float)
    t = np.arange(len(s))
    slope, intercept = np.polyfit(t, s.to_numpy(), 1)
    trend = np.clip(intercept + slope * t, 1e-9, None)
    ratio = pd.Series(s.to_numpy() / trend, index=s.index)
    idx = ratio.groupby(ratio.index.month).mean()
    idx = idx.reindex(range(1, 13)).fillna(1.0)
    return idx / idx.mean()


def forecast(data: dict, cfg: dict) -> pd.DataFrame:
    th = cfg["thresholds"]
    months = horizon_months(cfg)
    steps = np.arange(1, len(months) + 1)
    spend = data["monthly_spend"]
    vendors = data["vendors"].set_index("vendor_id")
    hc_hist = data["headcount"].pivot(index="month", columns="department", values="headcount").sort_index()
    hc_proj = project_headcount(data["headcount"], months, th["headcount_trend_months"])

    def base(dept: str, frame: pd.DataFrame) -> pd.Series:
        return frame.sum(axis=1) if dept == COMPANY_WIDE_OWNER else frame[dept]

    rows = []
    for c in data["contracts"].itertuples(index=False):
        if c.status == "terminated":
            continue
        hist = spend[spend["contract_id"] == c.contract_id].set_index("month").sort_index()
        prices = [price_at(c.unit_price, c.price_escalator_pct, c.price_escalator_pct, c.end_date, m)
                  for m in months]

        if c.billing_model == "per_seat":
            dept = vendors.loc[c.vendor_id, "owner_department"]
            recent = hist.iloc[-th["adoption_lookback_months"]:]
            adoption = (recent["seats_active"] / base(dept, hc_hist).reindex(recent.index)).mean()
            needed = np.ceil(base(dept, hc_proj).to_numpy() * adoption - 1e-9)
            qty = np.maximum(float(c.seats_contracted), needed)
            method = f"seats = headcount x adoption {adoption:.0%}, min contracted {c.seats_contracted}"
        elif c.billing_model == "usage":
            units = hist["units_used"]
            idx = seasonal_index(units)
            adjusted = units / units.index.month.map(idx).to_numpy()
            trend = _linear_projection(adjusted.iloc[-th["usage_trend_months"]:].to_numpy(float), steps)
            qty = np.maximum(0.0, trend * np.array([idx[m.month] for m in months]))
            method = f"{th['usage_trend_months']}-month trend x seasonal index"
        else:
            qty = np.ones(len(months))
            method = "annual value / 12"

        for m, q, p in zip(months, qty, prices):
            rows.append(dict(month=m, vendor_id=c.vendor_id, contract_id=c.contract_id,
                             billing_model=c.billing_model, forecast_qty=round(float(q), 2),
                             forecast_unit_price=round(p, 4), forecast_amount=round(float(q) * p, 2),
                             method=method))
    return pd.DataFrame(rows)


def fy_landing(data: dict, fc: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Per vendor: actuals year to date + forecast of the remaining months vs. the annual budget."""
    fy = cfg["scenario"]["fiscal_year"]
    spend, budget = data["monthly_spend"], data["budget"]
    actual = spend[spend["month"].dt.year == fy].groupby("vendor_id")["actual_amount"].sum()
    rest = fc[fc["month"].dt.year == fy].groupby("vendor_id")["forecast_amount"].sum()
    bud = budget[budget["month"].dt.year == fy].groupby("vendor_id")["budget_amount"].sum()

    out = data["vendors"][["vendor_id", "name", "category", "owner_department"]].copy()
    out["actual_ytd"] = out["vendor_id"].map(actual).fillna(0.0).round(2)
    out["forecast_rest_of_year"] = out["vendor_id"].map(rest).fillna(0.0).round(2)
    out["landing"] = (out["actual_ytd"] + out["forecast_rest_of_year"]).round(2)
    out["budget_fy"] = out["vendor_id"].map(bud).fillna(0.0).round(2)
    out["landing_vs_budget"] = (out["landing"] - out["budget_fy"]).round(2)
    out["landing_vs_budget_pct"] = np.where(out["budget_fy"] > 0,
                                            out["landing_vs_budget"] / out["budget_fy"].where(out["budget_fy"] > 0),
                                            np.nan)
    out.insert(0, "fiscal_year", fy)
    return out


def landing_by_category(landing: pd.DataFrame) -> pd.DataFrame:
    cols = ["actual_ytd", "forecast_rest_of_year", "landing", "budget_fy", "landing_vs_budget"]
    cat = landing.groupby(["fiscal_year", "category"], as_index=False)[cols].sum().round(2)
    cat["landing_vs_budget_pct"] = cat["landing_vs_budget"] / cat["budget_fy"]
    return cat
