# Prompt 8: interactive Overview and Budget vs. actual, and a shared visual system

**Dependency:** the views `v_kpis_by_category` and `v_variance_monthly` must exist in the live Supabase
project first. Apply `sql/patches/001_interactive_views.sql` once (it also grants read access).

```
Evolve the existing app into interactive dashboards. Keep the "executive cockpit" Overview as the quality
reference and the SA Executive Balance design system: the SA monogram file, the existing tokens (Warm Ivory,
Deep Forest #0B302B, Muted Sage #8FAF9E, Mineral Bronze #A56B45), Newsreader only for page titles,
IBM Plex Sans with tabular figures, IBM Plex Mono for labels, and the "Synthetic data" tag. English UI,
money in BRL.

GROUND RULES
- Database is read-only for the schema: no new tables, views, policies, functions or migrations.
- All figures come from the views named below, read with the existing public client
  (src/lib/public-db.server.ts). The front end may only filter rows and add them up for the active
  selection; never recompute a business rule. Percentages = summed variance / summed budget of the
  same rows; show "—" when the budget is zero.
- Keep routes, Excel exports, status editing, owner sign-in, permissions and the intake review flow.
- Loading, error, no rows and a real zero are four different states. A real zero shows "BRL 0" or "0".
  While a selection changes, never show the previous selection's numbers as if they were current.

CONFIRMED DATA SOURCES (verified in the database; every row reconciles to the cent)
- v_kpis (1 row): fiscal_year, anchor_date, fy_landing, fy_budget, landing_vs_budget,
  landing_vs_budget_pct, savings_ytd, cost_avoidance_ytd, renewals_next_90_days, urgent_decisions,
  value_at_risk_auto_renewal, recommended_annual_impact.
- v_kpis_by_category (1 row per category, NEW): the same columns plus category, same definitions as
  v_kpis; the five rows add up to v_kpis exactly. Categories with nothing to report return 0.
- v_fy_landing_by_category: category, landing, budget_fy, landing_vs_budget, landing_vs_budget_pct.
- v_renewals_due: contract_id, vendor_id, vendor_name, category, end_date, auto_renew, notice_days,
  decision_deadline, days_to_deadline, urgent, days_to_end, rule, recommendation,
  estimated_annual_impact, rationale, annual_value, status.
- v_monthly_trend: month, category, owner_department, actual, budget, forecast (null where a series has
  no value). Range: Jun 2025 to Nov 2027.
- v_variance_monthly (NEW): fiscal_year, scope ('fy_landing' | 'ytd'), month, category,
  owner_department, is_forecast, budget, price, volume, unbudgeted, landing. Every row:
  budget + price + volume + unbudgeted = landing. Months: Jan-Dec 2026 for 'fy_landing'
  (December is_forecast = true), Jan-Nov for 'ytd'; closed months are identical in both scopes.
  Use it for the waterfall instead of v_variance_waterfall (same totals).

1. OVERVIEW - category filter driven by the chart (src/components/overview-dashboard.tsx)
- Opens on "All categories": KPIs from v_kpis. The bar of the largest positive overrun stays Mineral
  Bronze; the selected bar gets a distinct selected state (Deep Forest outline and light sage row
  background) that does not rely on colour alone (also a check icon and aria-pressed).
- The bars are the category selector: say so in the subtitle ("Select a category to filter the page").
  Click, tap, or Enter/Space on a focused row selects that category for the whole page; clicking the
  selected bar again, or "Clear filters", returns to All categories. All bars stay visible.
- With a category selected: KPIs come from that category's v_kpis_by_category row (FY landing, budget,
  variance in BRL and %, auto-renewal exposure, savings YTD and cost avoidance kept separate). The
  Renewal decisions panel filters v_renewals_due by category: "{renewals_next_90_days} contracts end in
  the next 90 days", "{urgent_decisions} urgent", and the urgent list for that category. Keep the
  90-day count and the 120-day recommendation window as separate scopes.
- Show the active slice next to the page header ("Category: Cloud" with a clear button). The summary
  line under the chart follows the selection.
- Shorten KPI helper texts (e.g. exposure: "Auto-renewing, action recommended").

2. BUDGET VS. ACTUAL - one filter state, dropdowns, chart interactions (src/routes/budget.tsx)
- Replace the chip groups with a compact analysis bar: two accessible <select> controls, "Category"
  (All categories + the five) and "Department" (All departments + the ten), on one row on desktop,
  stacked on narrow screens; then the period control "Full year (actuals + forecast)" | "Year to date";
  then the active-filter chips and "Clear filters".
- One filter state for the page: {category, department, period, month, component}. Every card, chart
  and summary on the page uses it.
- Add a KPI band above the charts from v_variance_monthly rows for the current state: Budget, Landing,
  Variance (BRL and %), and the three components Price, Volume, Unbudgeted.
- Monthly spend (v_monthly_trend, filtered by category and department):
  - Actual = solid Deep Forest line, Forecast = dashed Deep Forest line, Budget = Muted Sage line with
    a different dash, each with a text label at the line end and in the legend.
  - Replace "Today" with "As of {anchor_date from v_kpis, e.g. 30 Nov 2026}".
  - Months of fiscal year 2026 (Jan-Dec 2026) are selectable by click or tap on the point, and by a
    keyboard-equivalent "Month" select next to the chart. Other months stay visible as context and are
    not selectable. The selected month is highlighted, named in full ("October 2026") in the active
    chips, and removable on its own.
  - A selected month filters v_variance_monthly to scope 'fy_landing' and that month: the KPI band and
    the waterfall show that month only.
  - Choosing Full year or Year to date while a month is selected removes the month (the chip
    disappears) and shows the whole period ('fy_landing' or 'ytd').
- From budget to landing (waterfall from v_variance_monthly for the current state):
  - Budget and Landing are totals; Price, Volume and Unbudgeted are components. Each step shows its
    value as a direct label; keep a zero baseline. Under it add a small component strip (horizontal
    bars from zero for Price, Volume, Unbudgeted) so small components stay readable without changing
    the main scale.
  - Selecting a component (click, tap or keyboard) highlights it and turns the monthly chart into that
    component's monthly contribution (bars per FY 2026 month from v_variance_monthly) with the lines
    kept faint for context; the KPI band shows the component's total and its share of the variance.
  - Selecting Budget shows its monthly profile; selecting Landing shows actuals to date
    (is_forecast = false) and forecast (is_forecast = true) separately.
  - Show the active slice and period next to both chart titles, e.g. "Cloud · Engineering · Full year".

3. SHARED LAYOUT AND COMPONENTS (all pages)
- One page container (same max width and side margins), one PageHeader component (eyebrow, Newsreader
  title, one-line description, optional active-filter area), one section spacing scale, one
  TableToolbar (count on the left, Export to Excel on the right) and one FilterBar.
- Deep Forest for primary actions and primary information; Mineral Bronze only for exceptions that need
  attention; states always in text or icon as well as colour.
- Renewals: description covers all contracts ending in the next 120 days, with or without auto-renewal.
  Columns prioritise vendor, decision deadline with the Urgent marker beside it, recommendation and
  status; on narrow screens secondary fields move into the expandable detail, and the status control
  stays visible. Tabular figures for values.
- Vendors: a search box filtering the list by vendor name; name emphasised; status and recommendation
  in fixed columns. Vendor detail: the next decision (recommendation, deadline, impact and the rule) and
  its evidence (utilization, benchmark) come before contract terms.
- Savings: Saving and Cost avoidance as two equal KPI cards; money right-aligned; notes stay on their
  event's row.
- Contract intake: each contract shows its check status first ("5 of 5 match" or "N differ", with icon
  and word); the first result is expanded and the rest are collapsible sections; Extracted and On file use
  the same formatting (dates as "10 Feb 2027", Yes/No, "60 days", "4.0%", "BRL 100,890.00") and the raw
  extracted value stays available on hover/expand. Keep the PDF links and the owner review card.
- Overview on mobile: decisions before the chart.

ACCEPTANCE CRITERIA
- Overview, All categories: BRL 18.51M landing vs BRL 17.54M budget, +5.5%, BRL 910.6K exposure,
  BRL 201.0K savings and BRL 122.7K cost avoidance, 6 contracts in 90 days, 2 urgent.
- Overview, Cloud selected: BRL 5.62M vs BRL 4.75M, +18.4%, BRL 873.3K over, exposure BRL 0, savings
  BRL 176.3K, cost avoidance BRL 0, 0 contracts in 90 days, 0 urgent, and the empty message in the
  decisions list; "Category: Cloud" shown. SaaS selected: BRL 4.04M vs BRL 3.92M, +3.1%, exposure
  BRL 910.6K, savings BRL 3.4K, cost avoidance BRL 44.7K, 5 in 90 days, 2 urgent (Dealstream,
  Helpdeskly). Clearing restores All categories.
- Budget vs. actual, Category = Cloud and Department = Engineering, Full year: Budget BRL 4.75M,
  Price -BRL 116.8K, Volume +BRL 990.1K, Unbudgeted BRL 0, Landing BRL 5.62M.
- Month = October 2026, all categories: Budget BRL 1.47M, Price -BRL 36.7K, Volume +BRL 142.0K,
  Unbudgeted +BRL 16.4K, Landing BRL 1.59M.
- In every supported slice Budget + Price + Volume + Unbudgeted = Landing (display rounding aside).
- The active slice is always visible; keyboard alone can select a category, a month and a component.
- Desktop (1280px) and mobile (375px) on every page: main information early, next action easy to find,
  no horizontal page scroll; routes, exports, status editing, sign-in and intake still work.
```
