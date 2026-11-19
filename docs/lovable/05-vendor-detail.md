# Prompt 5: Vendor detail

```
Build the Vendor detail page (/vendors/:vendorId) from view v_vendor_detail (one row per vendor),
plus a vendor list at /vendors (name, category, status, recommendation) linking to each page.

Sections:
1. Header: vendor_name, category, capability, criticality, risk_tier, status.
2. Contract terms card: contract_id, start_date, end_date, auto_renew, notice_days,
   decision_deadline, billing_model, unit_price (BRL per month), seats_contracted, annual_value,
   price_escalator_pct, termination_fee.
3. Seat utilization chart (only when billing_model = 'per_seat') from view v_seat_utilization
   filtered by contract_id: seats_active as a Deep Forest line and seats_contracted as a Muted Sage
   reference line, by month. Caption with utilization_3m as "Last 3 months: N% of seats used".
4. Price vs. public benchmark (only when benchmark_product is not null): unit_price vs.
   benchmark_price_per_seat, price_vs_benchmark_pct, and "Source: <benchmark_product>, list price as of
   <benchmark_as_of>" linking to benchmark_source_url (opens in a new tab). Note: "Public list
   price; enterprise buyers usually pay less."
5. Recommendation card: recommendation, estimated_annual_impact, and rule_explanation in plain
   language. When recommendation is null, show only rule_explanation.
6. FY figures: fy_landing vs. fy_budget.
```
