"""
etl_pipeline.py  —  Bluestock MF Analytics ETL (Days 1-2)
==========================================================
Extract  : 10 provided CSVs in data/raw/  (optionally live NAV from mfapi.in)
Transform: type-cast, validate, derive daily_return, build dim_date, map benchmarks
Load     : SQLite star schema (data/db/bluestock_mf.db) + processed CSV backups

Run:  python scripts/etl_pipeline.py
Idempotent: drops & recreates tables each run.
"""
from __future__ import annotations
import logging
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

# ---- paths (cross-platform, no hard-coded absolute paths) ----
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "db" / "bluestock_mf.db"
SCHEMA_SQL = ROOT / "sql" / "schema.sql"
PROC.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("etl")

# Map fund_master.benchmark strings -> index_name keys in 10_benchmark_indices.csv.
# Two TRI benchmarks have no matching series in the file -> fall back to closest available.
BENCHMARK_MAP = {
    "NIFTY 50 TRI": "NIFTY50",
    "NIFTY 100 TRI": "NIFTY100",
    "NIFTY 500 TRI": "NIFTY500",
    "NIFTY Midcap 150 TRI": "NIFTY_MIDCAP150",
    "BSE 250 SmallCap TRI": "BSE_SMALLCAP",
    "CRISIL Liquid Fund AI Index": "CRISIL_LIQUID",
    "CRISIL Dynamic Gilt Index": "CRISIL_GILT",
    "CRISIL Short Term Bond Index": "CRISIL_GILT",      # no short-bond series; gilt is the closest debt proxy
    "NIFTY Large Midcap 250 TRI": "NIFTY500",           # no series; broad-market proxy
    "NIFTY Midcap 50 TRI": "NIFTY_MIDCAP150",           # no series; midcap proxy
}


def _read(name: str, **kw) -> pd.DataFrame:
    df = pd.read_csv(RAW / name, **kw)
    log.info("read %-30s shape=%s", name, df.shape)
    return df


# ---------------------------------------------------------------- EXTRACT
def extract() -> dict[str, pd.DataFrame]:
    return {
        "fund":      _read("01_fund_master.csv", parse_dates=["launch_date"]),
        "nav":       _read("02_nav_history.csv", parse_dates=["date"]),
        "aum":       _read("03_aum_by_fund_house.csv", parse_dates=["date"]),
        "sip":       _read("04_monthly_sip_inflows.csv"),
        "cat":       _read("05_category_inflows.csv"),
        "folio":     _read("06_industry_folio_count.csv"),
        "perf":      _read("07_scheme_performance.csv"),
        "tx":        _read("08_investor_transactions.csv", parse_dates=["transaction_date"]),
        "holdings":  _read("09_portfolio_holdings.csv", parse_dates=["portfolio_date"]),
        "bench":     _read("10_benchmark_indices.csv", parse_dates=["date"]),
    }


# ---------------------------------------------------------------- VALIDATE
def validate(d: dict[str, pd.DataFrame]) -> None:
    """Hard data-quality gates. Raise on anything that would corrupt analytics."""
    fund_codes = set(d["fund"].amfi_code)
    assert d["fund"].amfi_code.is_unique, "duplicate amfi_code in fund_master"
    assert d["fund"].shape[0] == 40, f"expected 40 funds, got {d['fund'].shape[0]}"

    # referential integrity
    assert set(d["nav"].amfi_code) <= fund_codes, "NAV has codes missing from master"
    assert set(d["tx"].amfi_code) <= fund_codes, "transactions reference unknown funds"
    assert set(d["perf"].amfi_code) <= fund_codes, "performance references unknown funds"
    assert set(d["holdings"].amfi_code) <= fund_codes, "holdings reference unknown funds"

    # value sanity
    assert (d["nav"].nav > 0).all(), "non-positive NAV found"
    assert (d["tx"].amount_inr > 0).all(), "non-positive transaction amount"
    bad_er = d["fund"][(d["fund"].expense_ratio_pct < 0) | (d["fund"].expense_ratio_pct > 2.5)]
    if len(bad_er):
        log.warning("expense_ratio outside 0-2.5%% for %d funds (review): %s",
                    len(bad_er), bad_er.amfi_code.tolist())

    # benchmark coverage
    unmapped = set(d["fund"].benchmark) - set(BENCHMARK_MAP)
    assert not unmapped, f"benchmarks with no mapping rule: {unmapped}"

    # NAV completeness: every fund should have the same date grid
    counts = d["nav"].groupby("amfi_code").size()
    if counts.nunique() != 1:
        log.warning("NAV row counts differ across funds: min=%d max=%d", counts.min(), counts.max())
    log.info("validation OK — 40 funds, NAV %s->%s, %d benchmark series",
             d["nav"].date.min().date(), d["nav"].date.max().date(),
             d["bench"].index_name.nunique())


# ---------------------------------------------------------------- TRANSFORM
def build_dim_date(nav: pd.DataFrame) -> pd.DataFrame:
    """Full daily calendar across the NAV span (incl. weekends, for BI date logic)."""
    rng = pd.date_range(nav.date.min(), nav.date.max(), freq="D")
    dd = pd.DataFrame({"date": rng})
    dd["year"] = dd.date.dt.year
    dd["month"] = dd.date.dt.month
    dd["month_name"] = dd.date.dt.strftime("%b")
    dd["quarter"] = dd.date.dt.quarter
    # Indian FY: Apr-Mar
    fy_start = np.where(dd.date.dt.month >= 4, dd.year, dd.year - 1)
    dd["fy"] = [f"FY{y}-{str(y + 1)[-2:]}" for y in fy_start]
    dd["day_of_week"] = dd.date.dt.weekday
    dd["is_weekday"] = (dd.day_of_week < 5).astype(int)
    return dd


def transform_nav(nav: pd.DataFrame) -> pd.DataFrame:
    nav = nav.sort_values(["amfi_code", "date"]).drop_duplicates(["amfi_code", "date"])
    # daily simple return within each fund; first row per fund is NaN (no prior NAV)
    nav["daily_return"] = nav.groupby("amfi_code")["nav"].pct_change()
    return nav


def transform_fund(fund: pd.DataFrame) -> pd.DataFrame:
    fund = fund.copy()
    fund["benchmark_index"] = fund["benchmark"].map(BENCHMARK_MAP)
    return fund


def transform(d: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    d["fund"] = transform_fund(d["fund"])
    d["nav"] = transform_nav(d["nav"])
    d["dim_date"] = build_dim_date(d["nav"])
    # keep only the perf columns the schema expects (drop redundant name/house/etc.)
    perf_cols = ["amfi_code", "return_1yr_pct", "return_3yr_pct", "return_5yr_pct",
                 "benchmark_3yr_pct", "alpha", "beta", "sharpe_ratio", "sortino_ratio",
                 "std_dev_ann_pct", "max_drawdown_pct", "aum_crore", "expense_ratio_pct",
                 "morningstar_rating", "risk_grade"]
    d["perf"] = d["perf"][perf_cols]
    return d


# ---------------------------------------------------------------- LOAD
def load(d: dict[str, pd.DataFrame]) -> None:
    # 1. create schema via raw sqlite3 (executescript handles multi-statement DDL)
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA_SQL.read_text())
    con.commit()
    con.close()

    engine = create_engine(f"sqlite:///{DB_PATH}")
    table_map = {
        "dim_fund": d["fund"], "dim_date": d["dim_date"], "fact_nav": d["nav"],
        "fact_transactions": d["tx"], "fact_performance": d["perf"],
        "fact_portfolio": d["holdings"], "fact_aum": d["aum"],
        "fact_sip_industry": d["sip"], "fact_category_inflow": d["cat"],
        "fact_folio": d["folio"], "fact_benchmark": d["bench"],
    }
    for tbl, df in table_map.items():
        out = df.copy()
        for c in out.select_dtypes("datetime").columns:   # store ISO date strings
            out[c] = out[c].dt.strftime("%Y-%m-%d")
        out.to_sql(tbl, engine, if_exists="append", index=False)
        df.to_csv(PROC / f"{tbl}.csv", index=False)        # flat-file backup for Power BI
        log.info("loaded %-22s %6d rows", tbl, len(out))
    engine.dispose()


# ---------------------------------------------------------------- ORCHESTRATE
def main() -> None:
    log.info("=== Bluestock ETL start ===")
    d = extract()
    validate(d)
    d = transform(d)
    load(d)
    log.info("=== ETL done -> %s ===", DB_PATH)


if __name__ == "__main__":
    main()
