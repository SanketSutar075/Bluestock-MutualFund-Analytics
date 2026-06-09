-- ============================================================
-- queries.sql  —  10 analytical queries (Day 2 deliverable)
-- Run against data/db/bluestock_mf.db
--   sqlite3 data/db/bluestock_mf.db < sql/queries.sql
-- ============================================================

-- 1. Top 5 fund houses by latest-quarter AUM
SELECT fund_house, aum_lakh_crore
FROM fact_aum
WHERE date = (SELECT MAX(date) FROM fact_aum)
ORDER BY aum_lakh_crore DESC
LIMIT 5;

-- 2. Average monthly NAV per fund (2025) — sample of trend
SELECT f.scheme_name, strftime('%Y-%m', n.date) AS ym, ROUND(AVG(n.nav), 2) AS avg_nav
FROM fact_nav n JOIN dim_fund f ON f.amfi_code = n.amfi_code
WHERE n.date >= '2025-01-01'
GROUP BY f.scheme_name, ym
ORDER BY f.scheme_name, ym
LIMIT 20;

-- 3. SIP inflow YoY growth (months where it was reported)
SELECT month, sip_inflow_crore, yoy_growth_pct
FROM fact_sip_industry
WHERE yoy_growth_pct IS NOT NULL
ORDER BY month;

-- 4. Transaction count & total amount by state
SELECT state, COUNT(*) AS txns, ROUND(SUM(amount_inr)/1e7, 2) AS total_cr
FROM fact_transactions
GROUP BY state
ORDER BY total_cr DESC;

-- 5. Funds with expense ratio < 1%
SELECT scheme_name, fund_house, expense_ratio_pct
FROM dim_fund
WHERE expense_ratio_pct < 1.0
ORDER BY expense_ratio_pct;

-- 6. Transaction mix (SIP / Lumpsum / Redemption) share
SELECT transaction_type,
       COUNT(*) AS txns,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM fact_transactions), 1) AS pct
FROM fact_transactions
GROUP BY transaction_type;

-- 7. Average SIP amount by age group (SIP only)
SELECT age_group, ROUND(AVG(amount_inr)) AS avg_sip, COUNT(*) AS n
FROM fact_transactions
WHERE transaction_type = 'SIP'
GROUP BY age_group
ORDER BY age_group;

-- 8. Top 10 funds by provided Sharpe ratio
SELECT f.scheme_name, p.sharpe_ratio, p.return_3yr_pct, p.alpha
FROM fact_performance p JOIN dim_fund f ON f.amfi_code = p.amfi_code
ORDER BY p.sharpe_ratio DESC
LIMIT 10;

-- 9. T30 vs B30 contribution
SELECT city_tier,
       ROUND(SUM(amount_inr)/1e7, 2) AS total_cr,
       ROUND(100.0 * SUM(amount_inr) / (SELECT SUM(amount_inr) FROM fact_transactions), 1) AS pct
FROM fact_transactions
GROUP BY city_tier;

-- 10. Sector exposure across all equity portfolios (weighted by market value)
SELECT sector, ROUND(SUM(market_value_cr), 1) AS total_mv_cr,
       ROUND(AVG(weight_pct), 2) AS avg_weight_pct
FROM fact_portfolio
GROUP BY sector
ORDER BY total_mv_cr DESC;
