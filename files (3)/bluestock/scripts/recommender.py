"""
recommender.py  —  simple risk-based fund recommender (Day 6)
=============================================================
Input : investor risk appetite in {Low, Moderate, High}
Output: top-N funds by (recomputed) Sharpe ratio within the matching SEBI
        risk categories.

Usage:
    from recommender import recommend
    recommend("High", n=3)
or from the CLI:
    python scripts/recommender.py High
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"

# map a coarse appetite to the dataset's SEBI risk_category labels
APPETITE_MAP = {
    "Low":      ["Low", "Moderate"],
    "Moderate": ["Moderate", "Moderately High"],
    "High":     ["High", "Very High"],
}


def recommend(appetite: str, n: int = 3) -> pd.DataFrame:
    appetite = appetite.capitalize()
    if appetite not in APPETITE_MAP:
        raise ValueError(f"appetite must be one of {list(APPETITE_MAP)}")
    fund = pd.read_csv(P / "dim_fund.csv")
    met = pd.read_csv(P / "computed_metrics.csv")[["amfi_code", "sharpe_ratio",
                                                   "cagr_3yr_pct", "max_drawdown_pct"]]
    cand = fund[fund.risk_category.isin(APPETITE_MAP[appetite])].merge(met, on="amfi_code")
    cols = ["scheme_name", "sub_category", "risk_category",
            "sharpe_ratio", "cagr_3yr_pct", "max_drawdown_pct", "expense_ratio_pct"]
    return cand.nlargest(n, "sharpe_ratio")[cols].reset_index(drop=True)


if __name__ == "__main__":
    appetite = sys.argv[1] if len(sys.argv) > 1 else "Moderate"
    print(f"Top funds for a '{appetite}' risk appetite:\n")
    print(recommend(appetite).to_string(index=False))
