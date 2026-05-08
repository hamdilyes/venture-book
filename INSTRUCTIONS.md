# Processing instructions for venture-book

Two separate autonomous workflows. Each runs only when the user explicitly triggers it. Neither one asks the user any questions.

## Common rules (apply to both workflows)

- **Web search query format — exact, every time:**
  ```
  Fundraising rounds: <company name>
  ```
  Nothing else. No extra keywords, no founder names, no round qualifiers.
- **Trust the web search on any conflict** with the post or with the existing CSV value (amount, round, date, founders, funds, company name).
- **Never ask the user to confirm.** Write the row, log what changed, move on.
- **Don't fabricate.** If the web search doesn't give you enough data for a field, leave it blank rather than guess. For backfilled rows (Workflow 2), if you can't establish at least `amount_eur`, `round`, and `date` from the search, skip — don't add a partial row.
- **Standing extraction rules:**
  - YC mention → split into a `pre-seed` row (`amount_eur=500000`, `funds=Y Combinator`, no angels) + the announced round with `Y Combinator` removed. YC date: `YC SXX` → `20XX-06`; `YC WXX` → `20XX-01`.
  - Strategic-support companies (operating companies giving "strategic support" rather than venture funding, e.g. Pennylane, MyUnisoft, Convelio) are skipped — not in `funds`, not in `angels`.
  - Emojis stripped (🍐, ⚡, 🥷, etc.).
  - All-caps names title-cased (`Stéphanie ZOLESIO` → `Stéphanie Zolesio`).
  - Amounts kept as-is in `amount_eur` regardless of source currency (`$5.9M` → `5900000`); no currency conversion.
- **Schema** (preserve column order):
  ```
  company,description,amount_eur,round,date,founders,funds,angels
  ```
  - `description` ≤ 100 chars, one line. Quote with `"` if it has commas.
  - `date` is `YYYY-MM`.
  - `founders` / `funds` / `angels` are `;`-separated. Quote with `"` if any cell has commas.

---

## Workflow 1 — Process new posts in [data/dump.md](data/dump.md)

**Trigger:** user says **"go for it"** (or equivalent: "process the dump", "do it").

For each paragraph in [data/dump.md](data/dump.md), top-to-bottom:

1. Extract every field you can from the post text.
2. Run the standard `Fundraising rounds: <company name>` web search to verify and fill gaps.
3. Reconcile with the common rules. On conflict, web wins.
4. **Post-author fund**: if the dump is the user's own VC's posts (default assumption: Kima Ventures unless told otherwise this session), prepend that fund to `funds`. This rule applies only to Workflow 1.
5. Append the row to [data/fundraises.csv](data/fundraises.csv).
6. Apply the YC split if relevant (a second row).
7. Delete the processed paragraph (and its trailing blank line) from [data/dump.md](data/dump.md).
8. Continue until the file has no posts left.

When done, reply with one line:
> Processed N posts from `data/dump.md`. CSV is now at `data/fundraises.csv`.

---

## Workflow 2 — Refresh + backfill the CSV

**Trigger:** user says **"refresh csv"** (or equivalent: "go through the csv", "backfill the rounds", "audit the csv").

Run two passes over [data/fundraises.csv](data/fundraises.csv):

### Pass A — Refresh existing rows

For each row in the CSV:

1. Run `Fundraising rounds: <company name>` web search.
2. Compare each field (`description`, `amount_eur`, `round`, `date`, `founders`, `funds`, `angels`) against the search results.
3. **Update in place** any field where the web search disagrees with the current value. Trust the web.
4. Do NOT introduce the post-author fund rule here — that's a Workflow 1 thing. Only update funds if the web search names funds the row is missing.
5. Keep a tally of changes per row (for the summary).

### Pass B — Backfill earlier rounds

After Pass A, for each row whose `round` is `seed` or later (`series-a`, `series-b`, `series-c`, …):

1. Reuse the same `Fundraising rounds: <company name>` search results from Pass A (don't re-search).
2. Identify any earlier rounds the company has done that are **not** already in the CSV (compare by `(company, round)`).
3. For each such earlier round, append a new row **only if** you can establish at least `amount_eur`, `round`, and `date`. Fill the rest from the search (`founders`, `funds`, `description`); leave `angels` blank if not stated.
4. If you can't get those three minimum fields, skip — don't add a partial row.
5. Apply the YC split if applicable.

### Done message

Reply with a short summary:

> Refreshed N rows (M updated, K unchanged). Backfilled P earlier rounds.

If the CSV was changed, also reload the Streamlit app (it auto-reloads on file change).

---

## What this is NOT for

- Don't run either workflow proactively — only on the trigger phrase.
- Don't web-search for any other reason during normal editing.
- Don't make schema changes during these workflows. Schema changes require a separate explicit user instruction.
