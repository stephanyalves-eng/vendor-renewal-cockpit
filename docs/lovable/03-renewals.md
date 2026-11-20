# Prompt 3: Renewals (and public-key data access)

```
Two changes in this step.

PART A - DATA ACCESS (applies to the whole app, including the existing Overview)
- Read all view data with the public (anon/publishable) Supabase client, not with the service-role
  admin client. The database already grants SELECT on every view to anon and enforces row level
  security; the service-role key must not be needed to read anything.
- Replace the Overview reads that use supabaseAdmin with the public client, keeping the same queries,
  query keys, loading and error states. The page must look and behave exactly as it does now.
- Writes (Part B, owner only) use the signed-in user's session with the same public client, so row
  level security applies. Do not use the service-role key anywhere in the app.
- Database: read-only for the schema. Do not create, alter or drop tables, views, policies or
  functions; no migrations.

PART B - RENEWALS PAGE (/renewals), from view v_renewals_due (already sorted by decision_deadline)
- Table columns: vendor_name (link to /vendors/:vendor_id), category, end_date, auto_renew (Yes/No),
  notice_days, decision_deadline, days_to_deadline, recommendation, estimated_annual_impact (BRL),
  status. Default sort by decision_deadline ascending; allow sorting by estimated_annual_impact.
- When urgent is true: a warning icon plus the word "Urgent" in the deadline cell, never colour alone.
  Use Mineral Bronze for the urgent marker, consistent with the Overview.
- Clicking a row expands it (button with aria-expanded) to show rationale, utilization (as %),
  target_seats and consolidate_into when present.
- Summary line above the table: number of contracts, number urgent, and the sum of
  estimated_annual_impact, labelled "Estimated annual impact".
- Status editing (values: onboarding, active, renewal_window, renegotiating, terminated):
  - Visitors (not signed in): the status select works, but the change is saved only in the browser
    (localStorage, keyed by contract_id) and overrides the database value on screen. Show a small note
    "Demo: status changes stay in your browser" and a "Reset" link that clears them.
  - Signed-in owner: the same select runs update contracts set status = ... where contract_id = ...
    with the user's session. Database policies allow this only for admins; show an error message if
    the update is rejected or changes 0 rows.
- Wire the footer "Owner sign-in" link to Supabase email + password sign-in on a /signin route, with
  sign-out. No sign-up form.
- Mobile (375px): the table becomes stacked cards with the same fields; nothing overflows.
- Loading, error and empty states.

ACCEPTANCE
- Overview unchanged in look and figures, now read with the public client (no supabaseAdmin import left
  in the app).
- /renewals lists 15 contracts in decision_deadline order; 2 urgent (Dealstream 12 Dec, Helpdeskly
  16 Dec); estimated annual impact total BRL 1,042,321.80.
- As a visitor, changing a status updates the screen, survives a reload, and "Reset" restores the
  database value. No network write is made.
- Checked at 1280px and 375px.
```
