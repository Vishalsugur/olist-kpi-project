-- =====================================================================
-- Olist KPI queries in SQL (DuckDB dialect, runs directly on the CSVs)
-- Run all of them with:  python src/run_sql.py
-- Same KPIs as the Power BI measures, so you can talk through both in interviews.
-- =====================================================================

CREATE OR REPLACE VIEW FactOrderItems     AS SELECT * FROM read_csv_auto('data/processed/FactOrderItems.csv');
CREATE OR REPLACE VIEW FactOrders         AS SELECT * FROM read_csv_auto('data/processed/FactOrders.csv');
CREATE OR REPLACE VIEW DimCustomer        AS SELECT * FROM read_csv_auto('data/processed/DimCustomer.csv');
CREATE OR REPLACE VIEW DimProduct         AS SELECT * FROM read_csv_auto('data/processed/DimProduct.csv');
CREATE OR REPLACE VIEW DimSeller          AS SELECT * FROM read_csv_auto('data/processed/DimSeller.csv');
CREATE OR REPLACE VIEW FactLateRiskScores AS SELECT * FROM read_csv_auto('data/processed/FactLateRiskScores.csv');

-- Q1. Monthly revenue, orders, average order value and month-over-month growth (window function LAG)
WITH monthly AS (
    SELECT DATE_TRUNC('month', OrderDate)  AS month,
           SUM(Price)                      AS revenue,
           COUNT(DISTINCT OrderKey)        AS orders
    FROM FactOrderItems
    GROUP BY 1
)
SELECT month,
       ROUND(revenue, 0)                                                        AS revenue,
       orders,
       ROUND(revenue / orders, 2)                                               AS avg_order_value,
       ROUND(100.0 * (revenue / LAG(revenue) OVER (ORDER BY month) - 1), 1)     AS revenue_mom_pct
FROM monthly
ORDER BY month;

-- Q2. Like-for-like year-over-year growth (January-August of each year)
SELECT YEAR(OrderDate)                                   AS year,
       ROUND(SUM(Price), 0)                              AS revenue,
       COUNT(DISTINCT OrderKey)                          AS orders,
       ROUND(SUM(Price) / COUNT(DISTINCT OrderKey), 2)   AS avg_order_value
FROM FactOrderItems
WHERE MONTH(OrderDate) BETWEEN 1 AND 8
GROUP BY 1
ORDER BY 1;

-- Q3. Late delivery rate and review score by customer region (JOIN to a dimension)
SELECT c.Region,
       COUNT(*)                                FILTER (WHERE o.IsDelivered = 1)  AS delivered_orders,
       ROUND(100.0 * AVG(o.IsLate), 1)                                           AS late_rate_pct,
       ROUND(AVG(o.DeliveryDays), 1)                                             AS avg_delivery_days,
       ROUND(AVG(o.ReviewScore), 2)                                              AS avg_review
FROM FactOrders o
JOIN DimCustomer c ON c.CustomerKey = o.CustomerKey
GROUP BY c.Region
ORDER BY late_rate_pct DESC;

-- Q4. Review score by delivery timing (the key finding)
SELECT DelayBucket,
       COUNT(*)                                   AS orders,
       ROUND(AVG(ReviewScore), 2)                 AS avg_review,
       ROUND(100.0 * AVG(IsBadReview), 1)         AS bad_review_pct
FROM FactOrders
WHERE IsDelivered = 1
GROUP BY DelayBucket, DelayBucketSort
ORDER BY DelayBucketSort;

-- Q5. Seller scorecard: top 10 sellers by revenue with delivery and review KPIs (CTEs + RANK)
WITH seller_sales AS (
    SELECT SellerKey, SUM(Price) AS revenue, COUNT(DISTINCT OrderKey) AS orders
    FROM FactOrderItems
    GROUP BY SellerKey
),
seller_service AS (
    SELECT SellerKey, AVG(IsLate) AS late_rate, AVG(ReviewScore) AS avg_review
    FROM FactOrders
    GROUP BY SellerKey
)
SELECT RANK() OVER (ORDER BY ss.revenue DESC)   AS revenue_rank,
       s.SellerName, s.State,
       ROUND(ss.revenue, 0)                     AS revenue,
       ss.orders,
       ROUND(100.0 * sv.late_rate, 1)           AS late_rate_pct,
       ROUND(sv.avg_review, 2)                  AS avg_review
FROM seller_sales ss
JOIN seller_service sv USING (SellerKey)
JOIN DimSeller s       USING (SellerKey)
ORDER BY revenue_rank
LIMIT 10;

-- Q6. Revenue concentration: share of revenue from the top 1%, 10% and 20% of sellers (running total)
WITH ranked AS (
    SELECT SellerKey,
           SUM(Price)                                         AS revenue,
           ROW_NUMBER() OVER (ORDER BY SUM(Price) DESC)       AS rn,
           COUNT(*) OVER ()                                   AS n_sellers
    FROM FactOrderItems
    GROUP BY SellerKey
),
cumulative AS (
    SELECT rn, n_sellers,
           SUM(revenue) OVER (ORDER BY rn) / SUM(revenue) OVER () AS cum_share
    FROM ranked
)
SELECT pct AS top_pct_of_sellers,
       ROUND(100.0 * MAX(cum_share) FILTER (WHERE rn <= CEIL(n_sellers * pct / 100.0)), 1) AS revenue_share_pct
FROM cumulative, (VALUES (1), (10), (20)) t(pct)
GROUP BY pct
ORDER BY pct;

-- Q7. Repeat customer rate (customers with 2+ orders)
WITH orders_per_customer AS (
    SELECT CustomerKey, COUNT(DISTINCT OrderKey) AS n_orders
    FROM FactOrderItems
    GROUP BY CustomerKey
)
SELECT COUNT(*)                                                  AS customers,
       SUM(CASE WHEN n_orders > 1 THEN 1 ELSE 0 END)             AS repeat_customers,
       ROUND(100.0 * AVG(CASE WHEN n_orders > 1 THEN 1 ELSE 0 END), 2) AS repeat_rate_pct
FROM orders_per_customer;

-- Q8. Category performance: revenue share plus order-level satisfaction
--     (an order with items in two categories counts once in each, so join on distinct order-category pairs)
WITH order_category AS (
    SELECT DISTINCT i.OrderKey, p.Category
    FROM FactOrderItems i
    JOIN DimProduct p USING (ProductKey)
),
category_revenue AS (
    SELECT p.Category, SUM(i.Price) AS revenue
    FROM FactOrderItems i
    JOIN DimProduct p USING (ProductKey)
    GROUP BY p.Category
)
SELECT cr.Category,
       ROUND(cr.revenue, 0)                                      AS revenue,
       ROUND(100.0 * cr.revenue / SUM(cr.revenue) OVER (), 1)    AS revenue_share_pct,
       ROUND(100.0 * AVG(o.IsLate), 1)                           AS late_rate_pct,
       ROUND(100.0 * AVG(o.IsBadReview), 1)                      AS bad_review_pct
FROM category_revenue cr
JOIN order_category oc USING (Category)
JOIN FactOrders o      ON o.OrderKey = oc.OrderKey
GROUP BY cr.Category, cr.revenue
ORDER BY revenue DESC
LIMIT 10;

-- Q9. New customers per month (first purchase in that month)
SELECT DATE_TRUNC('month', OrderDate) AS month,
       COUNT(*)                       AS new_customers
FROM FactOrders
WHERE CustomerOrderNumber = 1
GROUP BY 1
ORDER BY 1;

-- Q10. How well the late-delivery model ranks orders (test period, Jun-Aug 2018)
SELECT RiskBand,
       COUNT(*)                                                         AS orders,
       ROUND(100.0 * AVG(ActualLate), 1)                                AS actual_late_pct,
       ROUND(100.0 * SUM(ActualLate) / SUM(SUM(ActualLate)) OVER (), 1) AS share_of_all_late_pct
FROM FactLateRiskScores
GROUP BY RiskBand, RiskBandSort
ORDER BY RiskBandSort;
