# Prompt 2b: Overview redesign ("executive cockpit")

Sent after prompt 2, with the reference screenshot attached. Replaces the Overview layout; the data
contract is unchanged.

```
Redesign the existing Overview page (/) as an "executive cockpit", following the attached reference
image for composition and hierarchy. The page must answer two questions at first glance: how far over or
under budget will the fiscal year land, and which contracts need a decision now?

The reference shows numbers and vendors from this synthetic scenario only as examples. Every value must
come from the views below at runtime.

KEEP (do not change)
- Navigation, the official SA monogram file, the "Synthetic data" tag, the existing footer (including the
  "Owner sign-in" link) and the existing routes and pages.
- The existing Supabase client, queries, design tokens, components and money helpers (src/lib/money.ts).
- Database: read-only. Do not create, alter or drop tables, views, policies or functions; no migrations.
  Do not compute business figures in the front end; use the view fields as returned.

LAYOUT (desktop)
1. Compact header row: editorial page title "Renewal overview" in Newsreader light (the only serif on the
   page) on the left; on the right a small IBM Plex Mono uppercase label
   "FY {v_kpis.fiscal_year} · AS OF {v_kpis.anchor_date formatted as 30 NOV 2026}".
2. One horizontal KPI band of four blocks, separated by hairline dividers, sharing one card frame:
   a. "FY landing" - the only dark block: Deep Forest #0B302B background, ivory text.
      Value v_kpis.fy_landing (compact BRL, e.g. "BRL 18.51M"); subline "vs. BRL {fy_budget} budget".
   b. "Budget variance" - value v_kpis.landing_vs_budget_pct with sign (e.g. "+5.5%"); subline
      "BRL {abs(landing_vs_budget)} over budget" with an up-arrow icon and the word "Over" when > 0,
      a down-arrow icon and "Under budget" when < 0, and "On budget" with no arrow when it is 0.
   c. "Auto-renewal exposure" - value v_kpis.value_at_risk_auto_renewal; subline
      "Auto-renewing contracts in the 120-day window with a recommendation other than renew".
   d. "Savings YTD" - value v_kpis.savings_ytd; a separate subline
      "BRL {cost_avoidance_ytd} cost avoidance". Never add the two together.
   Use tabular figures for all numbers.
3. Below the band, two columns: chart card on the left (~60% width), "Renewal decisions" panel on the
   right (~40%).

CHART CARD (left) - data: v_fy_landing_by_category
- Title "Landing vs. budget by category", subtitle "FY forecast and budget · BRL million".
- Legend: a sage swatch "Landing" and a thin vertical tick "FY budget".
- One row per category, sorted by landing descending: category name, a horizontal bar for landing, a
  thin dark vertical tick at budget_fy, and the signed landing_vs_budget_pct as a direct label at the
  row end. One common x-axis in BRL millions starting at zero, with labelled ticks.
- Bars are Muted Sage #8FAF9E. Only the category with the largest positive landing_vs_budget is Mineral
  Bronze #A56B45; if no category is over budget, nothing is highlighted.
- Rows are selectable by click and by keyboard (each row is a button or radio option, Tab to reach,
  Enter/Space to select, visible focus ring). The selected row gets a light ivory/sage background.
  Default selection: the bronze category, or the first row when there is none.
- Under the chart, a one-line summary for the selected category, from the same view row:
  "{category} · BRL {landing} landing / {budget_fy} budget · BRL {abs(landing_vs_budget)} over budget"
  (use "under budget" or "on budget" as appropriate, with the word, not only colour).

RENEWAL DECISIONS PANEL (right) - data: v_kpis and v_renewals_due
- Title "Renewal decisions". Subline "{v_kpis.renewals_next_90_days} contracts end in the next 90
  days". A small bronze badge "{v_kpis.urgent_decisions} urgent" with the word "urgent" always shown.
- List only rows of v_renewals_due where urgent = true, in decision_deadline order. Each row: a date
  badge with the decision_deadline day and month ("12 / DEC", bronze-tinted), vendor_name, and
  "{recommendation} · Auto-renews" (or "· Manual renewal" when auto_renew is false).
- Each row expands and collapses (a button with aria-expanded; a "+" / "−" icon) to show: rationale,
  "Estimated annual impact: BRL {estimated_annual_impact}" labelled as an estimate of the
  recommendation, and "Contract ends {end_date}".
- When there are no urgent rows: the short message "No decisions due in the next 30 days."
- A link at the bottom of the panel: "View all renewals →" to /renewals.
- Keep the two scopes distinct: the 90-day count is contracts ending soon; the list is urgent decisions
  from the 120-day recommendation window. Do not mix or recompute them.

RESPONSIVE AND ACCESSIBILITY
- Below the desktop breakpoint, the KPI band becomes a 2 x 2 grid; on very narrow screens, one column.
- On mobile and tablet, the Renewal decisions panel comes before the chart card.
- Money values must not overflow at 375px: use the compact format (BRL 18.5M / BRL 910.6K) in KPIs and
  let sublines wrap.
- Direction and urgency are always stated in words (Over, Under, On budget, urgent), never by colour
  alone. All interactive elements are reachable and operable by keyboard with a visible focus style.

STATES
- Separate loading skeletons and error messages for v_kpis, v_fy_landing_by_category and
  v_renewals_due, so one failing query does not blank the whole page.
- Empty states: no categories -> "No category data"; no urgent decisions -> message above.

ACCEPTANCE CRITERIA
- With the current data the page shows: FY landing BRL 18.51M vs. BRL 17.54M budget; +5.5% and
  BRL 969.6K over budget; auto-renewal exposure BRL 910.6K; savings BRL 201.0K and BRL 122.7K cost
  avoidance; 6 contracts in the next 90 days; 2 urgent (Dealstream 12 Dec, Helpdeskly 16 Dec); Cloud
  is the only bronze bar at +18.4%, selected by default.
- Selecting another category by mouse and by keyboard updates the summary line from that row.
- Expanding a decision shows rationale, estimated impact and end date; "View all renewals" opens
  /renewals.
- Checked at 1280px and 375px wide; the other routes (/budget, /renewals, /vendors/:vendorId, /savings,
  /intake) still load.
```
