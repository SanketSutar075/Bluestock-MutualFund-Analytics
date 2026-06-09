-- ============================================================
-- Bluestock MF Analytics — SQLite Star Schema
-- Grain documented per table. Columns match the real CSVs.
-- ============================================================

DROP TABLE IF EXISTS fact_nav;
DROP TABLE IF EXISTS fact_transactions;
DROP TABLE IF EXISTS fact_performance;
DROP TABLE IF EXISTS fact_portfolio;
DROP TABLE IF EXISTS fact_aum;
DROP TABLE IF EXISTS fact_sip_industry;
DROP TABLE IF EXISTS fact_category_inflow;
DROP TABLE IF EXISTS fact_folio;
DROP TABLE IF EXISTS fact_benchmark;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_fund;

-- ---------- DIMENSIONS ----------
-- Grain: one row per scheme (40)
CREATE TABLE dim_fund (
    amfi_code           INTEGER PRIMARY KEY,
    fund_house          TEXT NOT NULL,
    scheme_name         TEXT NOT NULL,
    category            TEXT,            -- Equity / Debt
    sub_category        TEXT,            -- Large Cap / Mid Cap / Liquid ...
    plan                TEXT,            -- Regular / Direct
    launch_date         DATE,
    benchmark           TEXT,            -- e.g. "NIFTY 100 TRI"
    benchmark_index     TEXT,            -- mapped key into fact_benchmark, e.g. "NIFTY100"
    expense_ratio_pct   REAL,
    exit_load_pct       REAL,
    min_sip_amount      INTEGER,
    min_lumpsum_amount  INTEGER,
    fund_manager        TEXT,
    risk_category       TEXT,
    sebi_category_code  TEXT
);

-- Grain: one row per calendar date in the NAV span
CREATE TABLE dim_date (
    date        DATE PRIMARY KEY,
    year        INTEGER,
    month       INTEGER,
    month_name  TEXT,
    quarter     INTEGER,
    fy          TEXT,        -- Indian financial year e.g. FY2024-25
    day_of_week INTEGER,     -- 0=Mon
    is_weekday  INTEGER      -- 1/0
);

-- ---------- FACTS ----------
-- Grain: one row per (fund, date). ~46,000
CREATE TABLE fact_nav (
    amfi_code       INTEGER NOT NULL,
    date            DATE NOT NULL,
    nav             REAL NOT NULL,
    daily_return    REAL,            -- computed: nav_t/nav_{t-1} - 1
    PRIMARY KEY (amfi_code, date),
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code),
    FOREIGN KEY (date)      REFERENCES dim_date(date)
);

-- Grain: one transaction. ~32,778
CREATE TABLE fact_transactions (
    tx_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    investor_id        TEXT,
    transaction_date   DATE,
    amfi_code          INTEGER,
    transaction_type   TEXT,         -- SIP / Lumpsum / Redemption
    amount_inr         INTEGER,
    state              TEXT,
    city               TEXT,
    city_tier          TEXT,         -- T30 / B30
    age_group          TEXT,
    gender             TEXT,
    annual_income_lakh REAL,
    payment_mode       TEXT,
    kyc_status         TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- Grain: one row per fund (provided, precomputed). 40
CREATE TABLE fact_performance (
    amfi_code          INTEGER PRIMARY KEY,
    return_1yr_pct     REAL,
    return_3yr_pct     REAL,
    return_5yr_pct     REAL,
    benchmark_3yr_pct  REAL,
    alpha              REAL,
    beta               REAL,
    sharpe_ratio       REAL,
    sortino_ratio      REAL,
    std_dev_ann_pct    REAL,
    max_drawdown_pct   REAL,
    aum_crore          INTEGER,
    expense_ratio_pct  REAL,
    morningstar_rating INTEGER,
    risk_grade         TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- Grain: one holding per fund. ~322
CREATE TABLE fact_portfolio (
    amfi_code         INTEGER,
    stock_symbol      TEXT,
    stock_name        TEXT,
    sector            TEXT,
    weight_pct        REAL,
    market_value_cr   REAL,
    current_price_inr REAL,
    portfolio_date    DATE,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- Grain: one row per (fund_house, quarter). 90
CREATE TABLE fact_aum (
    date           DATE,
    fund_house     TEXT,
    aum_lakh_crore REAL,
    aum_crore      INTEGER,
    num_schemes    INTEGER
);

-- Grain: one row per month (industry SIP). 48
CREATE TABLE fact_sip_industry (
    month                     TEXT PRIMARY KEY,
    sip_inflow_crore          INTEGER,
    active_sip_accounts_crore REAL,
    new_sip_accounts_lakh     REAL,
    sip_aum_lakh_crore        REAL,
    yoy_growth_pct            REAL
);

-- Grain: one row per (month, category). 144
CREATE TABLE fact_category_inflow (
    month            TEXT,
    category         TEXT,
    net_inflow_crore REAL
);

-- Grain: one row per month (folios). 21
CREATE TABLE fact_folio (
    month               TEXT PRIMARY KEY,
    total_folios_crore  REAL,
    equity_folios_crore REAL,
    debt_folios_crore   REAL,
    hybrid_folios_crore REAL,
    others_folios_crore REAL
);

-- Grain: one row per (index, date). ~8,050
CREATE TABLE fact_benchmark (
    date        DATE,
    index_name  TEXT,
    close_value REAL,
    PRIMARY KEY (index_name, date)
);

-- ---------- INDEXES (BI query speed) ----------
CREATE INDEX idx_nav_code    ON fact_nav(amfi_code);
CREATE INDEX idx_nav_date    ON fact_nav(date);
CREATE INDEX idx_tx_code     ON fact_transactions(amfi_code);
CREATE INDEX idx_tx_date     ON fact_transactions(transaction_date);
CREATE INDEX idx_tx_state    ON fact_transactions(state);
CREATE INDEX idx_bm_name     ON fact_benchmark(index_name);
