# Weekly renewal alert (Activepieces)

Every Monday at 08:00 (São Paulo) an e-mail lists the contracts whose decision deadline is within 30
days, read from the same Supabase view the app uses (`v_renewals_due`), so the e-mail and the dashboard
never disagree. A second, silent flow reads the database on Thursdays so the free Supabase project never
pauses for inactivity (it pauses after 7 days without requests).

All data is synthetic. "Days to deadline" is counted from the scenario date (30 Nov 2026), so the alert
lists the same contracts every week, exactly like the app.

## Flow 1: Renewal decisions due

| # | Step | Configuration |
| --- | --- | --- |
| 1 | **Schedule** (trigger) | Cron `0 8 * * 1`, timezone `America/Sao_Paulo` |
| 2 | **HTTP → Send request** | `GET https://ttcuicsbmujzpztexelw.supabase.co/rest/v1/v_renewals_due?select=vendor_name,category,decision_deadline,days_to_deadline,recommendation,estimated_annual_impact,auto_renew&days_to_deadline=lte.30&order=decision_deadline.asc`<br>Header `apikey: sb_publishable_TTlrktQPupv9-baWbq7KBQ_zV7ts9Or` (the public, read-only key; never the service role key) |
| 3 | **Code** | Paste [format-email.js](format-email.js). Input `rows` = the body of step 2. Returns `send`, `subject`, `html`, `text` |
| 4 | **Router / Branch** | Continue only when `send` (step 3) is `true`; an empty list sends nothing |
| 5 | **Gmail → Send email** | To: yourself. Subject: `subject` (step 3). Body type HTML: `html` (step 3) |

## Flow 2: Database keep-alive

| # | Step | Configuration |
| --- | --- | --- |
| 1 | **Schedule** (trigger) | Cron `0 8 * * 4`, timezone `America/Sao_Paulo` |
| 2 | **HTTP → Send request** | `GET https://ttcuicsbmujzpztexelw.supabase.co/rest/v1/scenario?select=anchor_date` with the same `apikey` header |

Together the two flows touch the database every three or four days, about 8 runs a month, well within
the Activepieces free plan.

## Files

- `format-email.js`: the code step, tested against the live view (2 contracts; nothing sent when empty;
  vendor names are HTML-escaped).
- `renewal-alert.json` and `keep-alive.json`: the flows exported from Activepieces.
- `renewal-alert.png`: a screenshot of the flow in the editor, used in the main README.
