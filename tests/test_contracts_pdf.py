"""Sample contracts: three PDFs whose terms match the contracts table (for the AI intake demo)."""
import pytest

from src.contracts_pdf import SAMPLE_CONTRACTS, build_contract_pdfs


@pytest.fixture(scope="module")
def pdfs(data, tmp_path_factory):
    return build_contract_pdfs(data, tmp_path_factory.mktemp("contracts"))


def test_three_pdfs(pdfs):
    assert len(pdfs) == 3 == len(SAMPLE_CONTRACTS)
    for p in pdfs:
        assert p.read_bytes().startswith(b"%PDF")


def test_samples_cover_the_three_cases(data):
    m = data["manifest"]
    assert set(SAMPLE_CONTRACTS) & set(m["urgent"])
    assert set(SAMPLE_CONTRACTS) & set(m["escalator"])
    assert set(SAMPLE_CONTRACTS) & set(m["above_benchmark"])


def test_pdf_text_carries_the_extractable_terms(data, pdfs):
    c = data["contracts"].set_index("contract_id")
    for cid, path in zip(SAMPLE_CONTRACTS, pdfs):
        raw = path.read_bytes()
        k = c.loc[cid]
        for needle in (
            "SYNTHETIC", cid, k["end_date"].isoformat(), f"{int(k['notice_days'])} days",
            f"{k['price_escalator_pct']:.1f}%", f"{k['termination_fee']:,.2f}",
            "Auto-renewal: Yes" if k["auto_renew"] else "Auto-renewal: No",
        ):
            assert needle.encode() in raw, (cid, needle)


def test_pdfs_are_reproducible(data, tmp_path):
    a = build_contract_pdfs(data, tmp_path / "a")
    b = build_contract_pdfs(data, tmp_path / "b")
    assert [p.read_bytes() for p in a] == [p.read_bytes() for p in b]
