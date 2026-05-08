# venture-book

An orderbook of venture fundraises, maintained manually from public announcements (LinkedIn posts and similar). All fundraises live as rows in a single CSV: [data/fundraises.csv](data/fundraises.csv).

## Data model

[data/fundraises.csv](data/fundraises.csv) holds one row per fundraise event (i.e. one row per `(company, round)` pair). Multi-value cells are joined by `;`.

| column        | type    | notes                                                              |
|---------------|---------|--------------------------------------------------------------------|
| `company`     | string  | Company name, e.g. `Cleo Labs`                                     |
| `description` | string  | One-line description of what the company does                      |
| `amount_eur`  | integer | Amount in euros, no separators, e.g. `1500000`                     |
| `round`       | string  | `pre-seed`, `seed`, `series-a`, etc. (lowercased, hyphenated)      |
| `date`        | string  | `YYYY-MM`, e.g. `2026-04`                                          |
| `founders`    | string  | Full names, `;`-separated                                          |
| `funds`       | string  | Institutional investors, `;`-separated                             |
| `angels`      | string  | Angel investors, `;`-separated                                     |

Example rows:

```csv
company,description,amount_eur,round,date,founders,funds,angels
Cleo Labs,AI platform mapping product regulatory compliance across countries,1500000,pre-seed,2026-04,Naomie Halioua;Anaelle Guez,Kima Ventures;Amplify;Financière Saint James;Deel Ventures,Boris Paillard;Ambre Soubiran;Stéphanie Zolesio;Charles Sutton
Sillage,AI signal engine for sales teams to detect real buying intent,2000000,pre-seed,2026-04,Arnaud Weiss;Arthur Coudouy,Kima Ventures;Drysdale Ventures;STATION F,
```

## Layout

```
venture-book/
├── README.md
├── app.py              # Streamlit app
├── requirements.txt
└── data/
    └── fundraises.csv
```

## UI

A Streamlit timeline view of the orderbook. A round-type toggle at the top (Pre-seed / Seed / Series A / …) shows one round at a time. The X-axis is months, auto-fit from the earliest to the latest deal in the data. Within each month, deals are stacked vertically with the largest amount at the top. Each deal shows only the company name and the amount (`EUR 1.5M`, `EUR 800k`); investor and founder names are hidden on the main view and surfaced in a detail view (TBD).

Run locally:

```
pip install -r requirements.txt
streamlit run app.py
```
