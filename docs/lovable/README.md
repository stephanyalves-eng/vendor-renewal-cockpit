# Front end in Lovable: build plan

The web app reads the views that this repository creates in Supabase. Lovable only draws the screens:
every number is already calculated and tested here, which keeps Lovable credits low and the figures
identical to the README. All data is synthetic.

## Setup (no Lovable credits)

1. **Database.** In the Supabase project, run in this order: `sql/schema.sql`, `sql/load.sql`,
   `sql/supabase_policies.sql`. With `psql`, from the repository root, using the session pooler
   connection string from the Supabase dashboard (*Connect* button):
   ```powershell
   psql "<connection string>" -v ON_ERROR_STOP=1 -f sql/schema.sql -f sql/load.sql -f sql/supabase_policies.sql
   ```
2. **Owner login.** Create your user in Supabase *Authentication → Users*, then add its id to
   `app_admins` in the SQL editor. Turn off public sign-ups in *Authentication → Sign In / Providers*.
3. **Lovable project.** Create it with prompt 1 (no backend), then connect the existing Supabase
   project in *Settings → General → External Supabase*. Do not enable Lovable Cloud.

## Prompts, in order

| # | File | Builds | Est. credits |
| --- | --- | --- | ---: |
| 1 | [01-shell.md](01-shell.md) | Layout, navigation, design system, monogram, empty pages. No backend | ~2 |
| 2 | [02-overview.md](02-overview.md) | KPI strip and landing vs. budget by category | ~2 |
| 3 | [03-renewals.md](03-renewals.md) | Renewal table, urgency, status editing | ~2 |
| 4 | [04-budget-vs-actual.md](04-budget-vs-actual.md) | Monthly trend with forecast, variance waterfall, filters | ~2–3 |
| 5 | [05-vendor-detail.md](05-vendor-detail.md) | Contract terms, seat utilization, benchmark, rule | ~2 |
| 6 | [06-savings-and-export.md](06-savings-and-export.md) | Savings tracker, Excel export on every table | ~2 |
| 7 | [07-contract-intake.md](07-contract-intake.md) | Stored extractions for visitors, live AI extraction for the owner | ~3 |
| – | Fixes, batched in 2–3 messages | | ~2–4 |
| | **Total** | | **~15–22** |

## Rules that keep credits low

- Send each prompt as written, one message per page. Stop and review after each page.
- No Plan mode (1 credit per message even when nothing is built).
- Batch fixes: one message with several corrections, never one message per correction.
- Small edits (a colour, a label, spacing) go straight to the front-end GitHub repository. They sync
  back to Lovable without a prompt.

## Keeping visitors from spending credits

| Cost source | Protection |
| --- | --- |
| Database reads | External Supabase: billed by Supabase (free plan), never by Lovable |
| Hosting | Publish the front-end repository on a free static host (Netlify, Vercel or Cloudflare Pages), not on Lovable hosting |
| AI extraction | Visitors only see stored results. Live extraction runs only for signed-in admins, checked inside the edge function |
| Writes | Visitors' status changes stay in their browser. Only admins write to the database (`sql/supabase_policies.sql`) |

Supabase pauses free projects after 7 days without activity. The weekly alert flow (Activepieces)
queries the database every Monday; add a second weekly query so the demo never pauses.
