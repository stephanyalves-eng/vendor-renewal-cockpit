# Vendor Spend & Renewal Cockpit

[![tests](https://github.com/stephanyalves-eng/vendor-renewal-cockpit/actions/workflows/ci.yml/badge.svg)](https://github.com/stephanyalves-eng/vendor-renewal-cockpit/actions/workflows/ci.yml)

> **Synthetic data.** Everything in this repository describes a fictional fintech and fictional
> vendors, generated from a fixed random seed. The only real-world values are public list prices in
> the benchmarks table, each with its source URL and the date it was checked.

A budget and contract-renewal analytics layer for the indirect-procurement team of a Brazilian
fintech (about 680 employees, BRL 18.5M annual third-party spend in the scenario). It answers three
questions a procurement lead gets asked every month:

1. **Will we land the fiscal year on budget?** If not, is that because of price, volume, or spend nobody planned?
2. **Which contracts need a decision before they auto-renew?** By when, and what should we do with each one?
3. **Where can we cut or consolidate spend?** How much is each action worth?

This repository is the data and logic layer. It produces the tables and SQL views that a web front end
and a weekly alert e-mail read from. The technical specification it was built against is in
[SPEC.md](SPEC.md) (in Portuguese).

## Key findings from the synthetic run

Scenario date: 30 Nov 2026 (November is the last closed month). Fiscal year = calendar 2026.

**1. FY2026 lands BRL 0.97M (5.5%) over budget, and cloud accounts for all of it.**

| Category | Budget FY | Landing (actuals + forecast) | vs. budget |
| --- | ---: | ---: | ---: |
| Cloud | 4,745,187 | 5,618,523 | **+873,336 (+18.4%)** |
| SaaS | 3,917,688 | 4,039,336 | +121,648 (+3.1%) |
| Marketing | 4,407,817 | 4,419,696 | +11,879 (+0.3%) |
| Professional services | 1,439,099 | 1,436,250 | −2,849 (−0.2%) |
| Data and security | 3,031,923 | 2,997,469 | −34,454 (−1.1%) |
| **Total** | **17,541,713** | **18,511,274** | **+969,561 (+5.5%)** |

**2. The overrun is volume, not price.** Splitting the full-year variance into three parts:

| Budget | Price | Volume | Unbudgeted | Landing |
| ---: | ---: | ---: | ---: | ---: |
| 17,541,713 | **−153,386** | **+991,828** | **+131,120** | 18,511,274 |

- *Price* is favourable. Renewals came in below the IPCA assumption in the budget, and three contracts
  were renegotiated down (BRL 201k of annualized savings, plus BRL 123k of cost avoidance).
- *Volume* is the problem. Cloud consumption grows about 3.5% a month while the budget planned 2%. That is
  an engineering capacity conversation, not a supplier negotiation.
- *Unbudgeted* is one AI-assistant tool (Promptly) adopted in May with no budget line: BRL 131k this year.

**3. 15 contracts renew within 120 days. Acting on the recommendations is worth BRL 1.04M a year.**

| Recommendation | Contracts | Estimated annual impact (BRL) |
| --- | ---: | ---: |
| Right-size licences | 5 | 377,952 |
| Consolidate overlapping tools | 4 | 350,112 |
| Renegotiate | 3 | 203,839 |
| Terminate | 1 | 110,419 |
| Renew as is | 2 | 0 |
| **Total** | **15** | **1,042,322** |

That is more than the whole FY2026 overrun, and it is available within one quarter.

**4. Two decisions are urgent.** Both contracts auto-renew if nobody acts:

| Vendor | Decision deadline | Recommendation | Impact (BRL/yr) |
| --- | --- | --- | ---: |
| Dealstream (CRM) | 12 Dec 2026 | Right-size from 177 to 103 seats (52% used) | 168,720 |
| Helpdeskly (support desk) | 16 Dec 2026 | Renegotiate a 12% escalator down to IPCA (4.5%) | 14,364 |

Other highlights: three video-conferencing tools (keep Confera, drop MeetLoop and Vidmo: BRL 235k).
The productivity suite costs BRL 102.25 per seat against a public list price of BRL 81.80 (BRL 184k a year
on 749 seats). A company-wide wiki has 12% of its seats in use: let it expire and save BRL 110k net of the
termination fee.

## Data

The generator ([src/generate.py](src/generate.py)) builds 18 months of history (Jun 2025 to Nov 2026) for
40 fictional vendors in five categories: SaaS, Cloud, Marketing, Professional services, Data and security.

| Table | What it holds |
| --- | --- |
| `vendors` | Fictional name, category, capability, owning department, criticality, risk tier |
| `contracts` | One contract per vendor: term, auto-renewal, notice period, billing model, price, seats, escalator, termination fee, status |
| `monthly_spend` | Actual spend per month, with active seats, usage units and billed quantity |
| `budget` | Monthly budget per vendor as quantity × unit price |
| `headcount` | Monthly headcount per department |
| `benchmarks` | Public list prices (real) mapped to the fictional vendors that sell the same kind of product |
| `savings` | Savings (vs. previous price) and cost avoidance (vs. first quote) events |

Patterns are **planted on purpose** so the analytics have something to find. Tests prove each one is found:
three groups of overlapping tools, five licence contracts under 60% utilization, one low-criticality tool
under 20%, two escalators above IPCA, one vendor priced above its public benchmark, six renewals in the next
90 days (two of them auto-renewing with the notice period about to close), one unbudgeted vendor appearing
mid-year, cloud growing with usage, and marketing with seasonal peaks.

**Benchmarks.** Four public list prices were checked on the vendors' own pricing pages on 19 Nov 2026
([data/reference/public_list_prices.csv](data/reference/public_list_prices.csv)). Where a page did not show
a clear price, currency and billing basis, the benchmark was left empty rather than guessed. USD prices are
converted at a scenario FX rate set in `config.yaml`.

## Method

```
config.yaml → generate → forecast → variance ─┐
                        └──────→ recommend ───┴→ export → data/supabase/*.csv → Supabase → views
```

| Step | Module | In one line |
| --- | --- | --- |
| Forecast | [src/forecast.py](src/forecast.py) | Per-seat follows headcount × adoption, usage follows trend × seasonality, fixed is annual value / 12, with escalators applied at renewal |
| Landing | [src/forecast.py](src/forecast.py) | Actuals year to date + forecast of the remaining months, against the annual budget |
| Variance | [src/variance.py](src/variance.py) | Price + volume + unbudgeted, equal to the total variance to the cent |
| Recommend | [src/recommend.py](src/recommend.py) | Terminate → consolidate → right-size → renegotiate → renew, first match wins, with a decision deadline |
| Contracts | [src/contracts_pdf.py](src/contracts_pdf.py) | Three sample contract PDFs for the front end's AI intake demo |
| Export | [src/export.py](src/export.py) | Runs everything, writes CSVs and PDFs |
| Schema | [sql/schema.sql](sql/schema.sql) | Tables plus `v_fy_landing`, `v_fy_landing_by_category` and `v_renewals_due` |

Every rule is explained in plain business language in [docs/methodology.md](docs/methodology.md). All
thresholds, the scenario date, the seed and the IPCA rate live in [config.yaml](config.yaml).

## How to reproduce

Requires Python 3.11.

```powershell
py -3.11 -m venv .venv
```

```powershell
.venv\Scripts\python -m pip install -r requirements.txt
```

```powershell
.venv\Scripts\python -m pytest
```

```powershell
.venv\Scripts\python -m src.export
```

The export writes:

- `data/processed/`: every table as CSV, with a `# SYNTHETIC DATA` header line.
- `data/supabase/`: the same files without the comment line, ready for Postgres `COPY`.
- `data/contracts/`: three sample contract PDFs.

To load the database, run `sql/schema.sql`, then `sql/load.sql` with `psql` from the repository root. In
the Supabase dashboard, you can instead import the files from `data/supabase/` in the order the tables are
created.

Same seed, same output: the test suite checks that the data and the CSV files are byte-for-byte reproducible.

**Database check.** [scripts/pg_check.sh](scripts/pg_check.sh) builds the database in a real Postgres from
`schema.sql` and loads every row of every CSV. It then saves the three views to files, and
[tests/test_postgres.py](tests/test_postgres.py) checks them against the Python figures to the cent.
GitHub Actions runs it on every push, against Postgres 17
([.github/workflows/ci.yml](.github/workflows/ci.yml)). The same workflow fails if the committed CSVs no
longer match a fresh export. Locally the check is skipped unless `PG_VIEWS_DIR` is set; set it and run:

```powershell
bash scripts/pg_check.sh
```

The script reads the standard `PG*` connection variables and drops only the cockpit's own tables and views
before rebuilding.

## Limitations

- **Synthetic data.** The patterns were planted, so finding them shows the rules work as designed, not that
  they would catch everything in a real ledger. Real data brings messy vendor masters, credit notes,
  prepayments and multi-currency invoices that this model ignores.
- **One contract per vendor, annual terms.** Real portfolios have multi-year deals, mid-term amendments and
  co-terming. Prices change only at renewal and there is no proration inside a month.
- **The forecast assumes the status quo.** Every live contract renews on its current terms, and the savings
  from recommendations are reported separately as upside. Usage trends use six months of data, and the seasonal
  index rests on one or two observations per calendar month.
- **Consolidation ignores switching costs.** Migration effort, the extra seats needed at the vendor you keep,
  and contract overlap during the move are not netted out of the impact.
- **Benchmarks are list prices.** Enterprise buyers usually pay below list, so "above benchmark" is a prompt
  to ask questions, not proof of overpaying. Prices were read from pages that may vary by region.
- **IPCA and FX are scenario assumptions** in `config.yaml`, not official figures.
- **The views are checked on plain Postgres 17, not on a Supabase project in CI.** Supabase-specific behaviour,
  such as the read policies for the `anon` role, was checked once by hand on Supabase: the schema applied
  cleanly and the security advisor flagged nothing.
