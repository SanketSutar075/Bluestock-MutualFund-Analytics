"""
compute_metrics.py  —  Performance & Risk Analytics (Day 4 + Day 6)
====================================================================
Reads the SQLite DB built by etl_pipeline.py and computes, PER FUND, from the
synthetic NAV history (this is the skill being graded — do NOT just copy
07_scheme_performance.csv; that file is kept only as a sanity reference):

  - annualised return, CAGR 1y/3y/5y
  - Sharpe, Sortino   (Rf = 6.5% RBI repo proxy, sqrt(252) annualisation)
  - Alpha (Jensen), Beta   (OLS of fund daily returns on its MAPPED benchmark)
  - Max Drawdown
  - Historical VaR 95% and CVaR (Day 6)
  - composite Scorecard (0-100) using the PDF's weighting

Output CSVs land in data/processed/ for the dashboard and report.
Run:  python scripts/compute_metrics.py
"""
from __future__ import annotations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "db" / "bluestock_mf.db"
PROC = ROOT / "data" / "processed"

RF_ANNUAL = 0.065          # RBI repo-rate proxy
TRADING_DAYS = 252
RF_DAILY = RF_ANNUAL / TRADING_DAYS


def load_frames():
    import sqlite3
    con = sqlite3.connect(DB)
    fund = pd.read_sql("SELECT * FROM dim_fund", con)
    nav = pd.read_sql("SELECT amfi_code, date, nav, daily_return FROM fact_nav", con,
                      parse_dates=["date"])
    bench = pd.read_sql("SELECT * FROM fact_benchmark", con, parse_dates=["date"])
    con.close()
    return fund, nav, bench


def benchmark_returns(bench: pd.DataFrame) -> pd.DataFrame:
    """Wide table of daily benchmark returns, one column per index_name."""
    wide = bench.pivot(index="date", columns="index_name", values="close_value").sort_index()
    return wide.pct_change()


def cagr(nav_fund: pd.Series, years: int) -> float:
    """CAGR over the trailing `years` using nearest available NAV dates."""
    nav_fund = nav_fund.dropna().sort_index()
    if nav_fund.empty:
        return np.nan
    end_date = nav_fund.index.max()
    start_target = end_date - pd.DateOffset(years=years)
    if nav_fund.index.min() > start_target:
        return np.nan                                  # not enough history
    start_nav = nav_fund.loc[:start_target].iloc[-1]   # last NAV on/before target
    end_nav = nav_fund.iloc[-1]
    return (end_nav / start_nav) ** (1 / years) - 1


def max_drawdown(nav_fund: pd.Series) -> float:
    nav_fund = nav_fund.dropna()
    running_max = nav_fund.cummax()
    dd = nav_fund / running_max - 1
    return dd.min()                                    # negative


def per_fund_metrics(code, g_nav, ret, bench_ret, bench_index):
    r = ret.dropna()
    n = len(r)
    out = {"amfi_code": code, "n_days": n}

    # annualised return & vol
    ann_ret = (1 + r).prod() ** (TRADING_DAYS / n) - 1
    ann_vol = r.std(ddof=1) * np.sqrt(TRADING_DAYS)
    out["annualised_return_pct"] = round(ann_ret * 100, 2)
    out["std_dev_ann_pct"] = round(ann_vol * 100, 2)

    out["cagr_1yr_pct"] = round((cagr(g_nav, 1) or np.nan) * 100, 2)
    out["cagr_3yr_pct"] = round((cagr(g_nav, 3) or np.nan) * 100, 2)
    out["cagr_5yr_pct"] = round((cagr(g_nav, 5) or np.nan) * 100, 2)

    # Sharpe (annualised) from daily excess returns
    excess = r - RF_DAILY
    out["sharpe_ratio"] = round(excess.mean() / r.std(ddof=1) * np.sqrt(TRADING_DAYS), 3)

    # Sortino: downside deviation uses only negative-excess days
    downside = excess[excess < 0]
    dd_std = np.sqrt((downside ** 2).mean()) if len(downside) else np.nan
    out["sortino_ratio"] = round(excess.mean() / dd_std * np.sqrt(TRADING_DAYS), 3) if dd_std else np.nan

    # Alpha / Beta vs mapped benchmark (align on dates, drop NaN)
    if bench_index in bench_ret.columns:
        joined = pd.concat([r.rename("f"), bench_ret[bench_index].rename("b")],
                           axis=1, sort=False).dropna()
        if len(joined) > 30:
            slope, intercept, rval, _, _ = stats.linregress(joined.b, joined.f)
            out["beta"] = round(slope, 3)
            out["alpha_ann_pct"] = round(intercept * TRADING_DAYS * 100, 2)   # Jensen alpha, annualised
            out["r_squared"] = round(rval ** 2, 3)
            out["benchmark_used"] = bench_index
        else:
            out.update(beta=np.nan, alpha_ann_pct=np.nan, r_squared=np.nan,
                       benchmark_used=bench_index)
    else:
        out.update(beta=np.nan, alpha_ann_pct=np.nan, r_squared=np.nan,
                   benchmark_used=None)

    # Max drawdown
    out["max_drawdown_pct"] = round(max_drawdown(g_nav) * 100, 2)

    # Historical VaR / CVaR at 95% on daily returns (Day 6)
    var95 = np.percentile(r, 5)
    out["var_95_daily_pct"] = round(var95 * 100, 2)
    out["cvar_95_daily_pct"] = round(r[r <= var95].mean() * 100, 2)
    return out


def build_scorecard(m: pd.DataFrame) -> pd.DataFrame:
    """Composite 0-100 per PDF Day-4 task 7 weighting.
    Higher is better; expense ratio & drawdown are inverted (less is better)."""
    s = m.copy()
    rank = lambda col, asc: s[col].rank(ascending=asc, pct=True) * 100
    s["score"] = (
        0.30 * rank("cagr_3yr_pct", True)        # higher return -> better
        + 0.25 * rank("sharpe_ratio", True)
        + 0.20 * rank("alpha_ann_pct", True)
        + 0.15 * rank("expense_ratio_pct", False)  # lower expense -> better
        + 0.10 * rank("max_drawdown_pct", True)    # less negative -> better
    ).round(1)
    return s.sort_values("score", ascending=False)


def main():
    fund, nav, bench = load_frames()
    bench_ret = benchmark_returns(bench)
    bmap = fund.set_index("amfi_code")["benchmark_index"].to_dict()

    rows = []
    for code, g in nav.groupby("amfi_code"):
        g = g.set_index("date").sort_index()
        rows.append(per_fund_metrics(code, g["nav"], g["daily_return"],
                                     bench_ret, bmap.get(code)))
    metrics = pd.DataFrame(rows)
    metrics = metrics.merge(
        fund[["amfi_code", "scheme_name", "fund_house", "sub_category",
              "expense_ratio_pct", "risk_category"]],
        on="amfi_code")

    scorecard = build_scorecard(metrics)

    PROC.mkdir(exist_ok=True)
    metrics.to_csv(PROC / "computed_metrics.csv", index=False)
    scorecard.to_csv(PROC / "fund_scorecard.csv", index=False)
    metrics[["amfi_code", "scheme_name", "beta", "alpha_ann_pct", "r_squared",
             "benchmark_used"]].to_csv(PROC / "alpha_beta.csv", index=False)
    metrics[["amfi_code", "scheme_name", "var_95_daily_pct",
             "cvar_95_daily_pct", "max_drawdown_pct"]].to_csv(
                 PROC / "var_drawdown_summary.csv", index=False)

    print("Top 8 funds by composite score:")
    print(scorecard[["scheme_name", "cagr_3yr_pct", "sharpe_ratio",
                     "alpha_ann_pct", "max_drawdown_pct", "score"]].head(8).to_string(index=False))
    print(f"\nWrote 4 CSVs to {PROC}")


if __name__ == "__main__":
    main()
