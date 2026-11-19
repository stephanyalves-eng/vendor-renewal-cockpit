"""Three sample supplier contracts as PDF, generated from the contracts table.

They feed the contract-intake page of the front end, where an AI step extracts the end date,
auto-renewal, notice period, price escalator and termination fee. Because the PDFs are built
from the same data, the extraction can be checked against the table. All parties are fictional.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

BUYER = "Aurora Pay Instituicao de Pagamento S.A. (fictional fintech)"

# Dealstream: urgent auto-renewal. Contractly: escalator above IPCA. Workwell Suite: per-seat
# price above the public benchmark.
SAMPLE_CONTRACTS = ["C013", "C019", "C016"]


def _clauses(c, vendor) -> list[tuple[str, str]]:
    seats = f"{int(c['seats_contracted'])} seats" if c["billing_model"] == "per_seat" else "as used"
    return [
        ("1. Parties", f"Buyer: {BUYER}. Supplier: {vendor['name']} (fictional supplier). "
                       f"Contract reference: {c['contract_id']}."),
        ("2. Scope", f"Provision of {vendor['capability'].replace('_', ' ')} services "
                     f"({vendor['category']}) to the Buyer's {vendor['owner_department']} team."),
        ("3. Term", f"Start date: {c['start_date'].isoformat()}. End date: {c['end_date'].isoformat()}. "
                    f"Renewal term: 12 months."),
        ("4. Renewal", f"Auto-renewal: {'Yes' if c['auto_renew'] else 'No'}. "
                       f"Notice period: {int(c['notice_days'])} days before the end date. "
                       + ("Without written notice the agreement renews automatically for another term."
                          if c["auto_renew"] else "The agreement expires unless both parties sign a renewal.")),
        ("5. Fees", f"Billing model: {c['billing_model']}. Unit price: BRL {c['unit_price']:,.2f} per month "
                    f"({seats}). Annual contract value: BRL {c['annual_value']:,.2f}. Invoiced monthly."),
        ("6. Price adjustment", f"Price escalator: {c['price_escalator_pct']:.1f}% applied to all fees at each renewal."),
        ("7. Termination", f"Early termination fee: BRL {c['termination_fee']:,.2f}, payable if the Buyer "
                           f"terminates before the end date for convenience."),
        ("8. Governing law", "Laws of the Federative Republic of Brazil. Courts of Sao Paulo, SP."),
    ]


def build_contract_pdfs(data: dict, out_dir: str | Path, contract_ids: list[str] | None = None) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    contracts = data["contracts"].set_index("contract_id")
    vendors = data["vendors"].set_index("vendor_id")
    styles = getSampleStyleSheet()
    paths = []
    for cid in contract_ids or SAMPLE_CONTRACTS:
        c = contracts.loc[cid].copy()
        c["contract_id"] = cid
        vendor = vendors.loc[c["vendor_id"]]
        path = out_dir / f"{cid}_{vendor['name'].lower().replace(' ', '_')}.pdf"
        doc = SimpleDocTemplate(str(path), pagesize=A4, invariant=1, pageCompression=0,
                                title=f"Supplier agreement {cid} (synthetic)", author="Synthetic data generator",
                                leftMargin=2.2 * cm, rightMargin=2.2 * cm)
        story = [
            Paragraph("SYNTHETIC SAMPLE CONTRACT - fictional parties, for demonstration only", styles["Italic"]),
            Spacer(1, 0.3 * cm),
            Paragraph(f"Software and Services Agreement - {vendor['name']}", styles["Title"]),
            Spacer(1, 0.4 * cm),
        ]
        for heading, body in _clauses(c, vendor):
            story += [Paragraph(heading, styles["Heading3"]), Paragraph(body, styles["BodyText"])]
        story += [Spacer(1, 1 * cm),
                  Paragraph("Signed for the Buyer: Head of Procurement. Signed for the Supplier: Account Director.",
                            styles["BodyText"])]
        doc.build(story)
        paths.append(path)
    return paths
