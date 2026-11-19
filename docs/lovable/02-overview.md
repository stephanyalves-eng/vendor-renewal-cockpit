# Prompt 2: Overview

Send after the external Supabase project is connected and loaded.

```
The Supabase project is now connected. Its tables and views already exist and are populated.
Rules for this and every later step:
- Do NOT create, alter or drop tables, views, policies or functions, and do not write migrations.
- Read only from the views named in each prompt, with the Supabase client. Never compute business
  figures in the front end; the views already hold the tested numbers.

Build the Overview page (/):

1. KPI strip from view v_kpis (one row):
   - "FY landing vs. budget": fy_landing and fy_budget, with landing_vs_budget in BRL and
     landing_vs_budget_pct as %. Over budget = up-arrow icon plus the word "Over"; under = "Under".
   - "Savings YTD": savings_ytd and cost_avoidance_ytd shown separately, labelled "Saving" and
     "Cost avoidance".
   - "Renewals in 90 days": renewals_next_90_days, with urgent_decisions as "N urgent" (icon + word).
   - "Value at risk of auto-renewal": value_at_risk_auto_renewal, with the hint "Auto-renewing
     contracts with a recommendation other than renew".
2. "Landing vs. budget by category": horizontal bar chart from view v_fy_landing_by_category.
   One bar per category = landing; a thin reference mark = budget_fy; direct label with
   landing_vs_budget_pct. Highlight (Mineral Bronze) only the category with the largest overrun;
   all other bars Muted Sage.
3. Under the chart, one sentence that reads the numbers from v_kpis, e.g.
   "Fiscal year 2026 lands BRL 0.97M (5.5%) over budget." Build it from the values, not hard-coded.
4. Loading and error states for both queries.
```
