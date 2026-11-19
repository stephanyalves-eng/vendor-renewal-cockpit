"""Every recommendation rule must find the pattern the generator planted for it."""
import math

import pandas as pd
import pytest

from src.recommend import recommend, utilization_table


@pytest.fixture(scope="module")
def rec(data, cfg):
    return recommend(data, cfg)


def by_contract(rec):
    return rec.set_index("contract_id")


# --- each rule finds its planted pattern -------------------------------------------------------

@pytest.mark.parametrize("planted, rule", [
    ("terminate", "terminate"),
    ("consolidate", "consolidate"),
    ("rightsize", "right_size"),
    ("escalator", "renegotiate"),
    ("above_benchmark", "renegotiate"),
    ("renew", "renew"),
])
def test_rule_finds_planted_pattern(data, rec, planted, rule):
    r = by_contract(rec)
    ids = data["manifest"][planted]
    assert ids, f"nothing planted for {planted}"
    assert (r.loc[ids, "rule"] == rule).all(), r.loc[ids, ["rule", "rationale"]]


def test_no_unplanted_findings_in_window(data, rec):
    m = data["manifest"]
    planted = set().union(*(m[k] for k in ("terminate", "consolidate", "rightsize", "escalator",
                                           "above_benchmark", "renew")))
    assert set(rec["contract_id"]) == planted


def test_only_contracts_inside_the_renewal_window(rec, cfg):
    anchor = pd.Timestamp(cfg["scenario"]["anchor_date"])
    days = (pd.to_datetime(rec["end_date"]) - anchor).dt.days
    assert ((days > 0) & (days <= cfg["thresholds"]["renewal_window_days"])).all()


def test_decision_deadline_is_end_minus_notice_and_before_end(data, rec):
    c = data["contracts"].set_index("contract_id")
    for row in rec.itertuples():
        assert row.decision_deadline == pd.Timestamp(c.loc[row.contract_id, "end_date"]) - pd.Timedelta(days=int(c.loc[row.contract_id, "notice_days"]))
        assert row.decision_deadline < row.end_date


def test_urgent_flags_the_two_auto_renewals(data, rec):
    assert sorted(rec.loc[rec["urgent"], "contract_id"]) == sorted(data["manifest"]["urgent"])
    assert rec.loc[rec["urgent"], "auto_renew"].all()


# --- impact formulas ---------------------------------------------------------------------------

def test_terminate_impact_is_annual_value_minus_fee(data, rec):
    c = data["contracts"].set_index("contract_id")
    for cid in data["manifest"]["terminate"]:
        expected = c.loc[cid, "annual_value"] - c.loc[cid, "termination_fee"]
        assert by_contract(rec).loc[cid, "estimated_annual_impact"] == pytest.approx(expected, abs=0.01)


def test_consolidate_into_highest_utilization_member(data, rec, cfg):
    util = utilization_table(data, cfg).set_index("contract_id")["utilization"]
    vendors = data["vendors"].set_index("vendor_id")
    c = data["contracts"].set_index("contract_id")
    r = by_contract(rec)
    for cid in data["manifest"]["consolidate"]:
        keeper = r.loc[cid, "consolidate_into"]
        assert keeper in data["manifest"]["overlap_keepers"]
        assert vendors.loc[c.loc[keeper, "vendor_id"], "capability"] == vendors.loc[c.loc[cid, "vendor_id"], "capability"]
        assert util[keeper] > util[cid]
        assert r.loc[cid, "estimated_annual_impact"] == pytest.approx(c.loc[cid, "annual_value"])


def test_right_size_to_peak_plus_buffer(data, rec, cfg):
    c = data["contracts"].set_index("contract_id")
    r = by_contract(rec)
    buffer = cfg["thresholds"]["rightsize_buffer_pct"]
    for cid in data["manifest"]["rightsize"]:
        target = math.ceil(r.loc[cid, "peak_active_seats"] * (1 + buffer))
        assert r.loc[cid, "target_seats"] == target
        cut = c.loc[cid, "seats_contracted"] - target
        assert cut > 0
        assert r.loc[cid, "estimated_annual_impact"] == pytest.approx(cut * c.loc[cid, "unit_price"] * 12, abs=0.01)


def test_renegotiate_escalator_impact_is_gap_to_ipca(data, rec, cfg):
    ipca = cfg["economics"]["ipca_annual_pct"]
    c = data["contracts"].set_index("contract_id")
    for cid in data["manifest"]["escalator"]:
        expected = c.loc[cid, "annual_value"] * (c.loc[cid, "price_escalator_pct"] - ipca) / 100
        assert by_contract(rec).loc[cid, "estimated_annual_impact"] == pytest.approx(expected, abs=0.01)


def test_renegotiate_benchmark_impact_is_gap_to_list_price(data, rec):
    c = data["contracts"].set_index("contract_id")
    bench = data["benchmarks"].set_index("vendor_id")["list_price_per_seat"]
    for cid in data["manifest"]["above_benchmark"]:
        k = c.loc[cid]
        expected = (k["unit_price"] - bench[k["vendor_id"]]) * k["seats_contracted"] * 12
        assert by_contract(rec).loc[cid, "estimated_annual_impact"] == pytest.approx(expected, abs=0.01)


def test_renew_has_zero_impact(data, rec):
    assert (by_contract(rec).loc[data["manifest"]["renew"], "estimated_annual_impact"] == 0).all()


def test_every_row_explains_itself(rec):
    assert rec["rationale"].str.len().gt(20).all()


# --- priority order and config-driven thresholds -----------------------------------------------

def test_priority_consolidate_beats_right_size(data, cfg):
    """Make an overlapping tool badly under-used: it must still be consolidated, not right-sized."""
    contracts = data["contracts"].copy()
    cid = data["manifest"]["consolidate"][0]
    contracts.loc[contracts["contract_id"] == cid, "seats_contracted"] *= 3
    r = recommend({**data, "contracts": contracts}, cfg).set_index("contract_id")
    assert r.loc[cid, "rule"] == "consolidate"


def test_thresholds_come_from_config(data, cfg):
    strict = {**cfg, "thresholds": {**cfg["thresholds"], "rightsize_utilization_max": 0.30}}
    r = recommend(data, strict).set_index("contract_id")
    assert (r.loc[data["manifest"]["rightsize"], "rule"] != "right_size").all()
    loose = {**cfg, "economics": {**cfg["economics"], "ipca_annual_pct": 15.0}}
    r = recommend(data, loose).set_index("contract_id")
    assert (r.loc[data["manifest"]["escalator"], "rule"] == "renew").all()
