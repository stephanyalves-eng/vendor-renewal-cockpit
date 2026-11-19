"""Price + volume + unbudgeted must equal the total variance, to the cent."""
import pandas as pd
import pytest

from src.forecast import forecast, fy_landing
from src.variance import decompose, variance, waterfall

COMPONENTS = ["price_var", "volume_var", "unbudgeted_var"]


def cents(s):
    return (s * 100).round().astype("int64")


@pytest.fixture(scope="module")
def fc(data, cfg):
    return forecast(data, cfg)


@pytest.fixture(scope="module")
def var(data, fc, cfg):
    return variance(data, fc, cfg)


@pytest.mark.parametrize("scope", ["ytd", "fy_landing"])
def test_components_sum_to_total_to_the_cent_per_row(var, scope):
    v = var[var["scope"] == scope]
    assert len(v) > 0
    total = cents(v["actual_amount"]) - cents(v["budget_amount"])
    assert (cents(v["total_var"]) == total).all()
    assert (cents(v["price_var"]) + cents(v["volume_var"]) + cents(v["unbudgeted_var"]) == total).all()


@pytest.mark.parametrize("scope", ["ytd", "fy_landing"])
def test_components_sum_to_total_to_the_cent_in_aggregate(var, scope):
    v = var[var["scope"] == scope]
    total = cents(v["actual_amount"]).sum() - cents(v["budget_amount"]).sum()
    assert sum(cents(v[c]).sum() for c in COMPONENTS) == total == cents(v["total_var"]).sum()


def test_price_component_matches_textbook_formula(var):
    """(P_actual - P_budget) x Q_actual, within one cent of rounding per row."""
    v = var[(var["unbudgeted_var"] == 0) & (var["actual_qty"] > 0)]
    exact = (v["actual_amount"] / v["actual_qty"] - v["budget_unit_price"]) * v["actual_qty"]
    assert (v["price_var"] - exact).abs().max() <= 0.01


def test_unbudgeted_vendor_is_all_unbudgeted(data, var):
    vid = data["manifest"]["unbudgeted_vendors"][0]
    v = var[var["vendor_id"] == vid]
    assert len(v) > 0
    assert (v["unbudgeted_var"] == v["actual_amount"]).all()
    assert (v["price_var"] == 0).all() and (v["volume_var"] == 0).all()
    # and no other vendor carries unbudgeted spend
    assert (var.loc[var["vendor_id"] != vid, "unbudgeted_var"] == 0).all()


def test_terminated_contract_shows_negative_volume(data, var, cfg):
    cid = data["manifest"]["terminated"][0]
    vid = data["contracts"].set_index("contract_id").loc[cid, "vendor_id"]
    after = var[(var["vendor_id"] == vid) & (var["scope"] == "ytd") & (var["month"] > pd.Timestamp("2026-06-01"))]
    assert len(after) > 0
    assert (after["volume_var"] == -after["budget_amount"]).all()
    assert (after["price_var"] == 0).all()


def test_escalator_above_ipca_creates_positive_price_variance(data, var):
    # Helpdeskly renewed in Jan 2026 at +12% while the budget assumed IPCA.
    vid = data["contracts"].set_index("contract_id").loc["C014", "vendor_id"]
    v = var[(var["vendor_id"] == vid) & (var["scope"] == "ytd")]
    assert v["price_var"].sum() > 0


def test_renewal_price_cut_creates_negative_price_variance(data, var):
    saving_vendors = data["savings"].loc[data["savings"]["type"] == "saving", "vendor_id"]
    # One cut takes effect in December, so the full-year landing scope is the fair test.
    v = var[(var["vendor_id"].isin(saving_vendors)) & (var["scope"] == "fy_landing")]
    assert (v.groupby("vendor_id")["price_var"].sum() < 0).all()


def test_cloud_growth_shows_as_volume_variance(data, var):
    v = var[(var["vendor_id"].isin(data["manifest"]["cloud_vendors"])) & (var["scope"] == "ytd")]
    assert v["volume_var"].sum() > 0
    assert v["volume_var"].sum() > abs(v["price_var"].sum())


def test_landing_scope_reconciles_with_fy_landing(data, fc, var, cfg):
    landing = fy_landing(data, fc, cfg)
    v = var[var["scope"] == "fy_landing"]
    assert v["actual_amount"].sum() == pytest.approx(landing["landing"].sum(), abs=0.05)
    assert v["budget_amount"].sum() == pytest.approx(landing["budget_fy"].sum(), abs=0.05)


def test_waterfall_walks_from_budget_to_landing(var):
    w = waterfall(var, scope="fy_landing")
    steps = w.set_index("step")["amount"]
    assert list(w["step"]) == ["budget", "price", "volume", "unbudgeted", "landing"]
    assert cents(pd.Series([steps["budget"] + steps["price"] + steps["volume"] + steps["unbudgeted"]]))[0] \
        == cents(pd.Series([steps["landing"]]))[0]


def test_decompose_handles_hand_made_case():
    """Budget 10 seats at 100; actual 12 seats at 110; a second, unbudgeted vendor spends 50."""
    actual = pd.DataFrame({"month": [pd.Timestamp("2026-01-01")] * 2, "vendor_id": ["A", "B"],
                           "actual_qty": [12, 1], "actual_amount": [1320.0, 50.0]})
    budget = pd.DataFrame({"month": [pd.Timestamp("2026-01-01")], "vendor_id": ["A"],
                           "budget_qty": [10], "budget_unit_price": [100.0], "budget_amount": [1000.0]})
    d = decompose(actual, budget).set_index("vendor_id")
    assert d.loc["A", "price_var"] == 120.0      # (110 - 100) x 12
    assert d.loc["A", "volume_var"] == 200.0     # (12 - 10) x 100
    assert d.loc["B", "unbudgeted_var"] == 50.0
    assert d["total_var"].sum() == 370.0
