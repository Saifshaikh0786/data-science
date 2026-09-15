-- Section 5: Business Metrics SQL Queries
-- All queries assume the DuckDB warehouse tables from Section 2 are loaded.

-- 1. Total crop arrivals (Quintals) by crop
SELECT crop, SUM(arrival_qtl) AS total_arrival_qtl
FROM fact_arrivals GROUP BY crop ORDER BY total_arrival_qtl DESC;

-- 2. Average modal price vs MSP by crop
SELECT crop, AVG(modal_price) AS avg_modal_price, AVG(msp) AS avg_msp,
       AVG(modal_price) - AVG(msp) AS avg_gap
FROM fact_prices WHERE modal_price IS NOT NULL AND msp IS NOT NULL
GROUP BY crop;

-- 3. Price crash instances (modal price below MSP)
SELECT COUNT(*) AS crash_count FROM fact_prices WHERE below_msp;
SELECT mandi_id, date, crop, modal_price, msp FROM fact_prices WHERE below_msp;

-- 4. Average transit time by destination
SELECT destination, AVG(transit_hours) AS avg_hours
FROM fact_transport WHERE transit_hours IS NOT NULL AND transit_hours >= 0
GROUP BY destination ORDER BY avg_hours DESC;

-- 5. Transit delay rate by destination
SELECT destination, AVG(CASE WHEN is_delayed THEN 1 ELSE 0 END) AS delay_rate
FROM fact_transport GROUP BY destination;

-- 6. Weather impact: rainfall vs national daily arrivals
SELECT corr(a.total_qtl, w.total_rainfall_mm) AS rainfall_arrival_corr
FROM (SELECT date, SUM(arrival_qtl) AS total_qtl FROM fact_arrivals GROUP BY date) a
JOIN fact_weather_daily w USING (date);

-- 7. Top 5 mandis by arrival volume
SELECT m.mandi_name, m.district, SUM(a.arrival_qtl) AS total_qtl
FROM fact_arrivals a JOIN dim_mandi m USING (mandi_id)
GROUP BY m.mandi_name, m.district ORDER BY total_qtl DESC LIMIT 5;

-- 8. Crop-wise arrival share
SELECT crop, SUM(arrival_qtl) AS qtl,
       SUM(arrival_qtl) * 100.0 / SUM(SUM(arrival_qtl)) OVER () AS pct_share
FROM fact_arrivals GROUP BY crop;

-- 9. Price arbitrage score
SELECT crop, date, MAX(modal_price) - MIN(modal_price) AS price_spread,
       MAX(modal_price) AS best_price, MIN(modal_price) AS worst_price
FROM fact_prices WHERE modal_price IS NOT NULL
GROUP BY crop, date ORDER BY price_spread DESC;
