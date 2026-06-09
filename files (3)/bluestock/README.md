# Bluestock MF Analytics — Capstone

End-to-end mutual-fund analytics pipeline over 10 AMFI/mfapi datasets.

## Run
```
pip install -r requirements.txt
python scripts/etl_pipeline.py      # builds data/db/bluestock_mf.db + processed CSVs
python scripts/compute_metrics.py   # writes performance/risk CSVs to data/processed/
```

## Layout
- `scripts/etl_pipeline.py` — Extract→Validate→Transform→Load (Days 1-2)
- `sql/schema.sql` — star schema (dim_fund, dim_date, 9 fact tables)
- `sql/queries.sql` — 10 analytical queries
- `scripts/compute_metrics.py` — Sharpe/Sortino/Alpha/Beta/MaxDD/VaR + scorecard (Days 4 & 6)
- `data/processed/` — flat CSV backups + metric outputs (feed Power BI)

## Data-reality notes
- NAV history is already clean (40×1150, no nulls/dupes) — no forward-fill needed.
- Join key is `amfi_code` everywhere.
- Benchmark strings ("NIFTY 100 TRI") are mapped to series keys ("NIFTY100") in etl BENCHMARK_MAP.
- Metrics are recomputed from NAV; 07_scheme_performance.csv kept as fact_performance (sanity ref only).
