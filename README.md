# 📊 Bluestock Mutual Fund Analytics Platform

> End-to-end Python analytics system: ETL pipeline → SQLite star schema → quantitative risk/return metrics → fund recommender → 4-tab Streamlit dashboard + 17-chart visual report suite.

---

## 🗂️ Project Structure

```
bluestock/
├── data/
│   ├── raw/                        # 10 source CSVs (fund master, NAV, AUM, SIP, etc.)
│   └── processed/                  # ETL output CSVs + SQLite DB
├── notebooks/
│   ├── 03_eda_analysis.ipynb       # Exploratory Data Analysis
│   ├── 04_performance_analytics.ipynb  # Return & risk metrics
│   └── 05_advanced_analytics.ipynb # VaR, CVaR, rolling Sharpe, HHI
├── scripts/
│   ├── etl_pipeline.py             # Extract → Validate → Transform → Load
│   ├── compute_metrics.py          # Quantitative analytics engine
│   └── recommender.py              # Risk-appetite based fund recommender
├── sql/
│   ├── schema.sql                  # Star schema DDL
│   └── queries.sql                 # Analytical SQL queries
├── reports/figures/                # 17 auto-generated charts (PNG)
├── notebooks/DashBoard.py          # 4-tab Streamlit dashboard
└── requirements.txt
```

---

## ⚙️ Tech Stack

| Layer | Tools |
|-------|-------|
| Language | Python 3.11 |
| Data Processing | Pandas, NumPy |
| Statistical Computing | SciPy (OLS regression, VaR) |
| Database | SQLite + SQLAlchemy |
| Visualization | Matplotlib, Seaborn, Plotly |
| Dashboard | Streamlit |
| Analytics | Jupyter Lab |

---

## 🔄 Pipeline Overview

### Stage 1 — ETL (`etl_pipeline.py`)
- **Extracts** 10 real-world CSVs: fund master, NAV history, AUM, SIP inflows, category inflows, folio count, scheme performance, investor transactions, portfolio holdings, benchmark indices
- **Validates** referential integrity (40 funds, NAV sanity, expense ratio gates, benchmark coverage)
- **Transforms** NAV into daily returns, builds `dim_date` (Indian FY calendar), maps benchmark indices
- **Loads** into SQLite star schema (11 tables) + CSV backups for Power BI

### Stage 2 — Metrics (`compute_metrics.py`)
Computes **from raw NAV history** (not pre-computed CSV):

| Metric | Detail |
|--------|--------|
| CAGR | 1yr / 3yr / 5yr trailing |
| Sharpe Ratio | Rf = 6.5% RBI proxy, √252 annualisation |
| Sortino Ratio | Downside deviation only |
| Jensen Alpha | OLS vs mapped benchmark |
| Beta | OLS regression of fund vs benchmark daily returns |
| Max Drawdown | Peak-to-trough NAV decline |
| VaR 95% | Historical Value-at-Risk |
| CVaR | Conditional VaR (Expected Shortfall) |
| Scorecard | Composite 0–100 weighted score |

### Stage 3 — Recommender (`recommender.py`)
- Maps investor risk appetite (Low / Moderate / High) to SEBI risk categories
- Ranks candidates by Sharpe ratio
- Returns top-N funds with scheme name, sub-category, CAGR, drawdown, expense ratio

### Stage 4 — Dashboard (`DashBoard.py`)
4-tab interactive Streamlit app:
- **Industry Overview** — AUM trends, SIP inflows, folio growth, sector allocation
- **Fund Performance** — NAV trends, return correlation heatmap, risk-return scatter
- **Investor Analytics** — Demographics, geography, transaction mix, churn
- **SIP & Market Trends** — Rolling Sharpe, HHI concentration, category inflows

---

## 📈 Visual Report Suite (17 Charts)

| Chart | Description |
|-------|-------------|
| 01_nav_trends | NAV history across funds |
| 02_aum_by_house | AUM breakdown by fund house |
| 03_sip_timeline | Monthly SIP inflow trend |
| 04_category_heatmap | Category-wise inflow heatmap |
| 05_demographics | Investor age/gender distribution |
| 06_geography | Geographic AUM distribution |
| 07_folio_growth | Industry folio count over time |
| 08_return_corr | Fund return correlation matrix |
| 09_sector_donut | Portfolio sector allocation |
| 10_tx_mix_volume | Transaction type mix & volume |
| 11_risk_return | Risk vs return scatter (all funds) |
| 12_expense_income | Expense ratio vs income analysis |
| 13_top_scorecard | Top funds by composite scorecard |
| d6_01_var_cvar | VaR & CVaR per fund |
| d6_02_rolling_sharpe | 90-day rolling Sharpe ratio |
| d6_03_churn | Investor churn analysis |
| d6_04_hhi | HHI sector concentration index |

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/SanketSutar075/Bluestock-MutualFund-Analytics.git
cd Bluestock-MutualFund-Analytics
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run ETL pipeline
```bash
python scripts/etl_pipeline.py
```

### 4. Compute metrics
```bash
python scripts/compute_metrics.py
```

### 5. Launch dashboard
```bash
streamlit run notebooks/DashBoard.py
```

### 6. Fund recommender (CLI)
```bash
python scripts/recommender.py High
python scripts/recommender.py Moderate
python scripts/recommender.py Low
```

---

## 📊 Key Results

- Processed **40 mutual funds** across 10 SEBI categories
- NAV history spanning **5+ years** of daily data
- Computed **9 quantitative metrics** per fund from raw NAV
- Generated **17 publication-ready charts**
- Recommender covers **Low / Moderate / High** risk profiles
- Star schema with **11 tables**, idempotent ETL reloads

---

## 🧠 Key Learnings

- Building production-grade ETL pipelines with hard validation gates
- Computing financial metrics (Alpha, Beta, Sharpe, VaR) from scratch using OLS regression
- Designing SQLite star schemas for analytical workloads
- Structuring multi-module Python projects with clean separation of concerns

---

## 👤 Author

**Sutar Sanket Nagnath**  
B.Tech Computer Engineering — MIT Academy of Engineering, Pune (2027)  
GitHub: [@SanketSutar075](https://github.com/SanketSutar075)  
Email: snsutar2004@gmail.com
