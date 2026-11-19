"""Forecast rules per billing model and the fiscal-year landing."""
import math

import numpy as np
import pandas as pd
import pytest

from src.forecast import fy_landing, forecast, landing_by_category, project_headcount


@pytest.fixture(scope="module")
def fc(data, cfg):
    return forecast(data, cfg)


@pytest.fixture(scope="module")
def landing(data, fc, cfg):
    return fy_landing(data, fc, cfg)


def horizon(cfg):
    start = pd.Timestamp(cfg["scenario"]["history_end"]) + pd.DateOffset(months=1)
    return list(pd.date_range(start, periods=cfg["scenario"]["forecast_horizon_months"], freq="MS"))


def test_forecast_never_negative(fc):
    assert (fc["forecast_amount"] >= 0).all()
    assert (fc["forecast_qty"] >= 0).all()


def test_forecast_covers_every_live_contract_and_month(data, fc, cfg):
    live = data["contracts"].loc[data["contracts"]["status"] != "terminated", "contract_id"]
    assert set(fc["contract_id"]) == set(live)
    assert sorted(fc["month"].unique()) == horizon(cfg)
    assert len(fc) == len(live) * cfg["scenario"]["forecast_horizon_months"]


def test_forecast_is_deterministic(data, cfg, fc):
    pd.testing.assert_frame_equal(fc, forecast(data, cfg))


def test_fixed_is_annual_over_12_then_escalated(data, fc):
    c = data["contracts"].set_index("contract_id")
    for cid, rows in fc[fc["billing_model"] == "fixed"].groupby("contract_id"):
        k = c.loc[cid]
        monthly = k["annual_value"] / 12
        end_month = pd.Timestamp(k["end_date"]).replace(day=1)
        for _, r in rows.iterrows():
            expected = monthly * (1 + k["price_escalator_pct"] / 100) if r["month"] > end_month else monthly
            assert r["forecast_amount"] == pytest.approx(expected, abs=0.01)


def test_per_seat_follows_headcount_and_escalates_at_renewal(data, fc):
    c = data["contracts"].set_index("contract_id")
    seat = fc[fc["billing_model"] == "per_seat"]
    assert (seat["forecast_qty"] >= seat["contract_id"].map(c["seats_contracted"]).astype(float)).all()
    # Helpdeskly (12% escalator) renews in January 2027: price jumps from February.
    hd = seat[seat["contract_id"] == "C014"].set_index("month")["forecast_unit_price"]
    assert hd[pd.Timestamp("2027-01-01")] == pytest.approx(120.00)
    assert hd[pd.Timestamp("2027-02-01")] == pytest.approx(120.00 * 1.12)


def test_per_seat_true_up_when_headcount_outgrows_contract(data, cfg):
    """If a company-wide tool covers fewer seats than active users, the forecast bills the true-up."""
    contracts = data["contracts"].copy()
    contracts.loc[contracts["contract_id"] == "C012", "seats_contracted"] = 600  # PeopleFlow, ~680 active
    pf = forecast({**data, "contracts": contracts}, cfg)
    pf = pf[pf["contract_id"] == "C012"].sort_values("month")
    assert (pf["forecast_qty"] > 600).all()
    assert pf["forecast_qty"].is_monotonic_increasing


def test_headcount_projection_is_monotonic_for_growing_company(data, cfg):
    proj = project_headcount(data["headcount"], horizon(cfg), cfg["thresholds"]["headcount_trend_months"])
    total = proj.sum(axis=1)
    assert total.is_monotonic_increasing
    assert total.iloc[0] > data["headcount"].groupby("month")["headcount"].sum().iloc[-1] * 0.99


def test_cloud_forecast_keeps_growing(data, fc):
    cloud = data["manifest"]["cloud_vendors"]
    hist = data["monthly_spend"][data["monthly_spend"]["vendor_id"].isin(cloud)]
    last3 = hist.groupby("month")["units_used"].sum().sort_index().iloc[-3:].mean()
    f = fc[fc["vendor_id"].isin(cloud)].groupby("month")["forecast_qty"].sum().sort_index()
    assert f.iloc[0] > last3
    assert f.iloc[-1] > f.iloc[0] * 1.2


def test_marketing_forecast_keeps_seasonal_peaks(data, fc, cfg):
    mkt = fc[fc["vendor_id"].isin(data["manifest"]["marketing_vendors"])]
    by_month = mkt.groupby("month")["forecast_amount"].sum()
    peak = by_month[by_month.index.month.isin(cfg["generator"]["marketing_peak_months"])]
    flat = by_month[~by_month.index.month.isin(cfg["generator"]["marketing_peak_months"])]
    assert peak.min() > 1.4 * flat.mean()


# --- fiscal-year landing -----------------------------------------------------------------------

def test_landing_is_actuals_plus_forecast(data, fc, landing, cfg):
    fy = cfg["scenario"]["fiscal_year"]
    spend = data["monthly_spend"]
    ytd = spend[spend["month"].dt.year == fy]["actual_amount"].sum()
    rest = fc[fc["month"].dt.year == fy]["forecast_amount"].sum()
    assert landing["actual_ytd"].sum() == pytest.approx(ytd, abs=0.01)
    assert landing["forecast_rest_of_year"].sum() == pytest.approx(rest, abs=0.01)
    assert (landing["landing"] - landing["actual_ytd"] - landing["forecast_rest_of_year"]).abs().max() < 0.01


def test_landing_compares_with_annual_budget(data, landing, cfg):
    fy = cfg["scenario"]["fiscal_year"]
    b = data["budget"]
    assert landing["budget_fy"].sum() == pytest.approx(b[b["month"].dt.year == fy]["budget_amount"].sum(), abs=0.01)
    assert (landing["landing_vs_budget"] - (landing["landing"] - landing["budget_fy"])).abs().max() < 0.01


def test_unbudgeted_vendor_lands_against_zero_budget(data, landing):
    vid = data["manifest"]["unbudgeted_vendors"][0]
    row = landing.set_index("vendor_id").loc[vid]
    assert row["budget_fy"] == 0
    assert row["landing"] > 0
    assert pd.isna(row["landing_vs_budget_pct"])


def test_category_rollup_matches_vendor_total(landing):
    cat = landing_by_category(landing)
    assert set(cat["category"]) == set(landing["category"])
    for col in ("actual_ytd", "forecast_rest_of_year", "landing", "budget_fy"):
        assert cat[col].sum() == pytest.approx(landing[col].sum(), abs=0.05)
