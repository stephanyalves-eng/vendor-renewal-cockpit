# Prompt 1: app shell (no backend)

Attach `assets/sa-monogram-c2-forest.svg` to this message.

```
Build the shell of "Renewal Cockpit", a web app for the procurement team of a fictional fintech. It
answers three questions: Will we land the fiscal year on budget? Which contracts need a decision before
they auto-renew? Where can we cut or consolidate spend?

IMPORTANT
- Do NOT enable Lovable Cloud and do not create any backend, database, auth or edge function yet.
  I will connect an existing Supabase project in the next step. Pages show empty states for now.
- All data is synthetic. Show a small "Synthetic data" tag in the header on every page.

STRUCTURE
- Header: the attached monogram SVG top-left (use the file as is, do not redraw it), app name,
  "Synthetic data" tag, navigation.
- Pages and routes: Overview (/), Budget vs. actual (/budget), Renewals (/renewals),
  Vendor detail (/vendors/:vendorId), Savings (/savings), Contract intake (/intake).
- Footer: "Synthetic data. Source and method: github.com/stephanyalves-eng/vendor-renewal-cockpit"
  and a small, quiet "Owner sign-in" link (no function yet).
- Each page: a Newsreader title, a one-sentence description, and an empty state card.

DESIGN SYSTEM (follow strictly; define as CSS variables / Tailwind theme tokens)
- Colors: Warm Ivory #F6F3E8 page background; Deep Forest #0B302B for headings, primary text
  accents and the primary button; Muted Sage #8FAF9E for secondary series and quiet fills;
  Mineral Bronze #A56B45 as the single highlight, at most one highlighted element per view.
  Body text near-black on ivory.
- Typography: Newsreader (serif, light) only for page titles; IBM Plex Sans for UI, body and numbers
  with tabular figures; IBM Plex Mono uppercase for small labels and eyebrows.
- Cards: white, 1px hairline border, 4px radius, no shadows. Buttons and inputs: 2px radius.
  No gradients, no glassmorphism, no emoji.
- Charts (for later pages): zero baseline, labelled axes with units, rows-only gridlines, direct labels
  where possible, one highlighted series with the rest greyed. Meaning by icon plus word, never colour
  alone.
- Money: BRL, formatted like "BRL 18.5M" in KPIs and "BRL 1,234,567" in tables.
- Copy in English, sentence case, no exclamation marks. Responsive down to 375px.
```
