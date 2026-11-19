"""Export: every CSV says it is synthetic, Supabase copies load cleanly, output is reproducible."""
import re

import pandas as pd
import pytest

from src.export import SUPABASE_TABLES, run
from tests.test_generate import REAL_BRANDS


@pytest.fixture(scope="module")
def out(tmp_path_factory, cfg):
    root = tmp_path_factory.mktemp("export")
    run(cfg, root)
    return root


def test_every_processed_csv_has_synthetic_header(out):
    files = list((out / "processed").glob("*.csv"))
    assert len(files) >= len(SUPABASE_TABLES)
    for f in files:
        first = f.read_text(encoding="utf-8").splitlines()[0]
        assert first.startswith("# SYNTHETIC DATA"), f.name


def test_supabase_copies_have_no_comment_lines_and_same_rows(out):
    for table in SUPABASE_TABLES:
        clean = (out / "supabase" / f"{table}.csv").read_text(encoding="utf-8")
        assert not clean.startswith("#")
        a = pd.read_csv(out / "processed" / f"{table}.csv", comment="#")
        b = pd.read_csv(out / "supabase" / f"{table}.csv")
        pd.testing.assert_frame_equal(a, b)
    assert (out / "supabase" / "SYNTHETIC_DATA.md").exists()


def test_no_real_vendor_names_outside_benchmarks(out):
    for f in (out / "processed").glob("*.csv"):
        if f.name == "benchmarks.csv":
            continue
        text = f.read_text(encoding="utf-8")
        body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
        for brand in REAL_BRANDS:
            assert not re.search(rf"\b{re.escape(brand)}\b", body, re.IGNORECASE), (f.name, brand)


def test_sample_contracts_written(out):
    assert len(list((out / "contracts").glob("*.pdf"))) == 3


def test_export_is_reproducible(out, cfg, tmp_path):
    run(cfg, tmp_path)
    for f in (out / "processed").glob("*.csv"):
        assert f.read_bytes() == (tmp_path / "processed" / f.name).read_bytes(), f.name


def test_dates_and_booleans_load_into_postgres_types(out):
    c = pd.read_csv(out / "supabase" / "contracts.csv")
    assert set(c["auto_renew"].astype(str).str.lower()) <= {"true", "false"}
    assert pd.to_datetime(c["end_date"], format="%Y-%m-%d").notna().all()
    s = pd.read_csv(out / "supabase" / "monthly_spend.csv")
    assert s["month"].str.fullmatch(r"\d{4}-\d{2}-01").all()
