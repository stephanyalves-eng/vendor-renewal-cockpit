import pytest

from src.config import load_config


@pytest.fixture(scope="session")
def cfg():
    return load_config()


@pytest.fixture(scope="session")
def data(cfg):
    from src.generate import generate

    return generate(cfg)


def last_months(df, n):
    """Rows of monthly_spend for the last n months of history."""
    months = sorted(df["month"].unique())[-n:]
    return df[df["month"].isin(months)]


def utilization(data, lookback):
    """Average active / contracted seats over the last `lookback` months, per contract."""
    spend = last_months(data["monthly_spend"], lookback)
    seats = data["contracts"].set_index("contract_id")["seats_contracted"]
    per_seat = spend[spend["contract_id"].isin(seats.dropna().index)]
    active = per_seat.groupby("contract_id")["seats_active"].mean()
    return (active / seats.reindex(active.index)).rename("utilization")
