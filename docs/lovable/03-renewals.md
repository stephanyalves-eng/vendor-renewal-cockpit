# Prompt 3: Renewals

```
Build the Renewals page (/renewals) from view v_renewals_due (already sorted by decision_deadline).

Table columns: vendor_name (link to /vendors/:vendor_id), category, end_date, auto_renew (Yes/No),
notice_days, decision_deadline, days_to_deadline, recommendation, estimated_annual_impact (BRL),
status. Sort by decision_deadline ascending by default; allow sorting by impact.

- When urgent is true: a warning icon plus the word "Urgent" in the deadline cell, never colour alone.
- Clicking a row expands it to show rationale (plain-language reason for the recommendation),
  utilization (as %), target_seats and consolidate_into when present.
- Summary line above the table: number of contracts, number urgent, and the sum of
  estimated_annual_impact.

Status editing (status values: onboarding, active, renewal_window, renegotiating, terminated):
- Visitors (not signed in): the status select works, but the change is saved only in the browser
  (localStorage, keyed by contract_id) and overrides the database value on screen. Show a small note
  "Demo: status changes stay in your browser" and a "Reset" link that clears them.
- Signed-in owner: the same select updates contracts.status in Supabase
  (update contracts set status = ... where contract_id = ...). Database policies already allow this
  only for admins; show an error message if the update is rejected.
- Wire the footer "Owner sign-in" link to Supabase email + password sign-in on a /signin route, with
  sign-out. No sign-up form.
```
