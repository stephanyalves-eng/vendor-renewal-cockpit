"""The generator must be reproducible, valid, and plant every pattern listed in SPEC.md."""
import re
from datetime import timedelta

import pandas as pd
import pytest

from src.generate import CATEGORIES, BILLING_MODELS, STATUSES, SAVINGS_TYPES, generate
from tests.conftest import utilization

REAL_BRANDS = [
    "zoom", "slack", "docusign", "github", "google", "microsoft", "asana", "figma", "notion",
    "atlassian", "jira", "confluence", "salesforce", "hubspot", "aws", "amazon", "azure", "oracle",
    "sap", "workday", "zendesk", "okta", "1password", "dropbox", "adobe", "meta", "facebook",
    "serasa", "datadog", "splunk", "twilio", "mailchimp", "gupy", "totvs", "embraer", "miro",
    "stripe", "teams", "webex", "clicksign", "cloudflare",
]


def window_contracts(data, cfg, days):
    anchor = pd.Timestamp(cfg["scenario"]["anchor_date"])
    c = data["contracts"]
    delta = (pd.to_datetime(c["end_date"]) - anchor).dt.days
    return c[(delta > 0) & (delta <= days) & (c["status"] != "terminated")]


# --- reproducibility ---------------------------------------------------------------------------

def test_same_seed_same_data(cfg, data):
    again = generate(cfg)
    for name in ("vendors", "contracts", "monthly_spend", "budget", "headcount", "benchmarks", "savings"):
        pd.testing.assert_frame_equal(data[name], again[name])


def test_different_seed_changes_data(cfg, data):
    other = generate({**cfg, "seed": cfg["seed"] + 1})
    assert not data["monthly_spend"]["actual_amount"].equals(other["monthly_spend"]["actual_amount"])


# --- shape and validity ------------------------------------------------------------------------

def test_shape(cfg, data):
    assert len(data["vendors"]) == cfg["generator"]["n_vendors"] == 40
    assert data["vendors"]["vendor_id"].is_unique
    assert data["contracts"]["vendor_id"].is_unique
    months = sorted(data["monthly_spend"]["month"].unique())
    assert len(months) == 18
    assert months[0] == pd.Timestamp(cfg["scenario"]["history_start"])
    assert months[-1] == pd.Timestamp(cfg["scenario"]["history_end"])


def test_enums(data):
    assert set(data["vendors"]["category"]) == set(CATEGORIES)
    assert set(data["contracts"]["billing_model"]) == set(BILLING_MODELS)
    assert set(data["contracts"]["status"]) <= set(STATUSES)
    assert set(data["savings"]["type"]) == set(SAVINGS_TYPES)


def test_amounts_valid(data):
    spend = data["monthly_spend"]
    assert (spend["actual_amount"] >= 0).all()
    assert (data["budget"]["budget_amount"] >= 0).all()
    assert (data["headcount"]["headcount"] > 0).all()
    # amounts are stored to the cent
    assert (spend["actual_amount"].round(2) == spend["actual_amount"]).all()


def test_budget_amount_is_qty_times_price(data):
    b = data["budget"]
    assert ((b["budget_qty"] * b["budget_unit_price"] - b["budget_amount"]).abs() <= 0.005 + 1e-9).all()


def test_decision_deadline_before_end(data):
    c = data["contracts"]
    deadline = pd.to_datetime(c["end_date"]) - pd.to_timedelta(c["notice_days"], unit="D")
    assert (c["notice_days"] > 0).all()
    assert (deadline < pd.to_datetime(c["end_date"])).all()


def test_vendor_names_are_fictional(data):
    for name in data["vendors"]["name"]:
        for brand in REAL_BRANDS:
            assert not re.search(rf"\b{re.escape(brand)}\b", name, re.IGNORECASE), name


# --- benchmarks: only verified public prices ---------------------------------------------------

def test_benchmarks_have_source_and_date(data):
    b = data["benchmarks"]
    assert len(b) > 0
    assert b["source_url"].str.startswith("https://").all()
    assert b["as_of"].notna().all()
    assert (b["list_price_per_seat"] > 0).all()


def test_benchmarks_only_for_per_seat_vendors_with_published_price(data):
    b = data["benchmarks"].merge(data["contracts"], on="vendor_id")
    assert (b["billing_model"] == "per_seat").all()
    assert len(data["benchmarks"]) < len(data["vendors"])  # the rest stay without a benchmark


# --- planted patterns --------------------------------------------------------------------------

def test_three_overlap_groups(data):
    v = data["vendors"][data["vendors"]["vendor_id"].isin(
        data["contracts"].loc[data["contracts"]["status"] != "terminated", "vendor_id"])]
    sizes = v.groupby("capability").size()
    groups = sizes[sizes > 1]
    assert len(groups) == 3
    assert sorted(groups.tolist()) == [2, 2, 3]


def test_five_per_seat_contracts_below_60pct(cfg, data):
    t = cfg["thresholds"]
    util = utilization(data, t["utilization_lookback_months"])
    active = data["contracts"].set_index("contract_id")["status"] != "terminated"
    util = util[active.reindex(util.index)]
    low = util[(util >= t["terminate_utilization_max"]) & (util < t["rightsize_utilization_max"])]
    assert len(low) == 5
    assert set(low.index) == set(data["manifest"]["rightsize"])


def test_one_terminate_candidate(cfg, data):
    t = cfg["thresholds"]
    util = utilization(data, t["utilization_lookback_months"])
    very_low = util[util < t["terminate_utilization_max"]].index
    assert list(very_low) == data["manifest"]["terminate"]


def test_two_escalators_above_ipca(cfg, data):
    c = data["contracts"]
    above = c[c["price_escalator_pct"] > cfg["economics"]["ipca_annual_pct"]]
    assert sorted(above["contract_id"]) == sorted(data["manifest"]["escalator"])


def test_six_renewals_in_90_days_two_urgent_auto_renew(cfg, data):
    t = cfg["thresholds"]
    near = window_contracts(data, cfg, t["near_term_renewal_days"])
    assert len(near) == 6
    anchor = pd.Timestamp(cfg["scenario"]["anchor_date"])
    deadline = pd.to_datetime(near["end_date"]) - pd.to_timedelta(near["notice_days"], unit="D")
    urgent = near[near["auto_renew"] & ((deadline - anchor).dt.days <= t["urgent_deadline_days"])]
    assert len(urgent) == 2
    # every decision deadline in the renewal window is still ahead of the anchor date
    window = window_contracts(data, cfg, t["renewal_window_days"])
    w_deadline = pd.to_datetime(window["end_date"]) - pd.to_timedelta(window["notice_days"], unit="D")
    assert (w_deadline > anchor).all()


def test_all_planted_rule_cases_sit_inside_renewal_window(cfg, data):
    window = set(window_contracts(data, cfg, cfg["thresholds"]["renewal_window_days"])["contract_id"])
    m = data["manifest"]
    for key in ("consolidate", "rightsize", "terminate", "escalator", "above_benchmark", "renew"):
        assert set(m[key]) <= window, key


def test_one_unbudgeted_vendor_appears_mid_year(cfg, data):
    budgeted = set(data["budget"]["vendor_id"])
    spenders = set(data["monthly_spend"]["vendor_id"])
    unbudgeted = spenders - budgeted
    assert sorted(unbudgeted) == data["manifest"]["unbudgeted_vendors"]
    assert len(unbudgeted) == 1
    first = data["monthly_spend"].loc[data["monthly_spend"]["vendor_id"].isin(unbudgeted), "month"].min()
    assert first.year == cfg["scenario"]["fiscal_year"] and 3 <= first.month <= 9


def test_cloud_grows_with_usage(data):
    spend = data["monthly_spend"].merge(data["vendors"], on="vendor_id")
    cloud = spend[spend["category"] == "Cloud"].groupby("month")["units_used"].sum().sort_index()
    assert cloud.iloc[-6:].mean() > 1.3 * cloud.iloc[:6].mean()


def test_marketing_has_seasonal_peaks(cfg, data):
    spend = data["monthly_spend"].merge(data["contracts"][["contract_id", "billing_model"]], on="contract_id")
    spend = spend.merge(data["vendors"], on="vendor_id")
    mkt = spend[(spend["category"] == "Marketing") & (spend["billing_model"] == "usage")]
    by_month = mkt.groupby("month")["actual_amount"].sum()
    peaks = by_month[by_month.index.month.isin(cfg["generator"]["marketing_peak_months"])]
    others = by_month[~by_month.index.month.isin(cfg["generator"]["marketing_peak_months"])]
    assert peaks.min() > 1.4 * others.mean()


def test_one_terminated_contract_stops_spending(data):
    c = data["contracts"]
    term = c[c["status"] == "terminated"]
    assert len(term) == 1
    last = data["monthly_spend"].loc[data["monthly_spend"]["contract_id"].isin(term["contract_id"]), "month"].max()
    assert last <= pd.to_datetime(term["end_date"].iloc[0])


def test_savings_events_have_positive_impact(data):
    s = data["savings"]
    assert (s["annualized_impact"] > 0).all()
    assert (s["negotiated_price"] < s["baseline_price"]).all()


def test_contracts_predate_history_except_new_vendor(cfg, data):
    """Only the planted new (unbudgeted) vendor may start inside the history window."""
    c = data["contracts"].merge(data["vendors"], on="vendor_id")
    late = c[pd.to_datetime(c["start_date"]) > pd.Timestamp(cfg["scenario"]["history_start"])]
    assert sorted(late["vendor_id"]) == data["manifest"]["unbudgeted_vendors"]
