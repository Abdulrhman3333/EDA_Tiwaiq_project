# Quran Exams Dashboard

An interactive Streamlit dashboard built from the EDA notebook on the exam log of a Quran memorization
charity in Jeddah (~534k exams, 2002-2025). Every page starts with the question it answers, shows the
chart, explains **how to read it**, and ends with a plain-language **key takeaway**.

| Page | Question it answers |
|---|---|
| Overview | What does the whole programme look like at a glance? |
| Volume & Seasonality | How many exams per year, which months, new vs returning students, which weekdays? |
| COVID Impact | Did the pandemic change volume, pass rate or absences? |
| Branch Progression | How hard is each branch, where do students drop out, how long does each step take? |
| Teachers, Mosques & Sectors | Who carries the workload? How do results differ? |
| Students | How far do students get? Standout and struggling cases (ids only, never names). |
| Data Quality & Notes | What is missing, what was cleaned, what the limits are, glossary. |

Sidebar filters (years, sectors) apply to every page.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Without a processed dataset the app starts in **demo mode** with clearly labelled, invented sample data
so you can explore the layout. Build the real dataset as follows.

## Use the real data

1. Put the two raw exports in `data/raw/`:
   - `old_system_old.xls`
   - `old_system_new.xls`
2. Run the pipeline (it is the notebook's cleaning, step by step):
   ```bash
   python -m src.prepare_data
   ```
   It writes `data/processed/exams.parquet`. **Student names are not written to this file.**
3. `streamlit run app.py` now uses the real data (the demo banner disappears).

The `.xls` files are really HTML tables; the script converts them to CSV the first time and reuses the CSV after.
Raw and processed data are git-ignored on purpose (they contain information about children).

## Project layout

```
app.py                  entry point: navigation + global filters
views/                  one file per page (layout, charts, takeaways)
src/config.py           constants: branches, colours, COVID window
src/prepare_data.py     raw .xls -> clean parquet (the notebook pipeline)
src/data.py             loading, filters, demo-data generator
src/analytics.py        every number behind the charts (pure pandas, cached)
src/ui.py               KPI cards, callouts, chart styling
.streamlit/config.toml  theme
```

Analytics are separated from the pages: `src/analytics.py` has no plotting code, so each calculation can be
tested or reused (for example in a notebook) on its own.

## Notes and assumptions carried over from the notebook

- COVID window = March 2020 - December 2021 (change `COVID_START` / `COVID_END` in `src/config.py`).
- Branch numbers are treated as ordered levels; their real meaning should be confirmed with the charity.
- Pass rate = passed / attended (absences excluded). Scores are meaningful for passed exams only.
- Years with fewer than 500 exams (2007: lost data) are left out of year comparisons.
- Many early student ids were rebuilt from names, so student-level numbers are indicative.
- The Classera system (2025 onward) is not included, so 2025 volume is understated.

## Deploy

Push the repo (without `data/`) to GitHub and deploy on Streamlit Community Cloud, or run it inside the
charity's network with `streamlit run app.py --server.port 8501`. Because the data concerns children,
prefer private hosting and upload only `data/processed/exams.parquet` to the server.
