# KPI dictionary

Every measure in the Power BI model, grouped by display folder. The DAX is in [`powerbi/measures.dax`](../powerbi/measures.dax).
Expected values for validating the measures are in [`kpi_expected_values.csv`](kpi_expected_values.csv).

**Grain reminder:** sales measures read `FactOrderItems` (one row per item, canceled orders excluded); delivery and satisfaction
measures read `FactOrders` (one row per order, all statuses).

## Sales

| Measure | Definition | Why it matters | Format |
|---|---|---|---|
| **Revenue** | Sum of item prices on orders that were not canceled or unavailable. Excludes freight. | Headline size of the business. | `"R$" #,0` |
| **Freight Revenue** | Sum of freight charged to customers. |  | `"R$" #,0` |
| **GMV** | Gross merchandise value: everything the customer paid for products and freight. | Standard marketplace size metric. | `"R$" #,0` |
| **Orders** | Number of distinct orders with at least one sold item. |  | `#,0` |
| **Items Sold** | Number of order lines. |  | `#,0` |
| **Avg Order Value** | Revenue / Orders. | Separates growth from more orders vs. bigger baskets. | `"R$" #,0.00` |
| **Items per Order** | Items Sold / Orders. |  | `0.00` |
| **Freight % of Revenue** | Freight Revenue / Revenue. | High freight share discourages purchases, especially in remote regions. | `0.0%` |
| **Active Customers** | Distinct customers (real people, customer_unique_id) who bought in the period. |  | `#,0` |
| **Active Sellers** | Distinct sellers with at least one sale in the period. |  | `#,0` |
| **Revenue per Customer** | Revenue / Active Customers. |  | `"R$" #,0.00` |

## Time intelligence

| Measure | Definition | Why it matters | Format |
|---|---|---|---|
| **Last Data Date** | Last day of the data (31 Aug 2018), regardless of filters. Read from FactOrders because the last two days only have canceled orders. | Used to compare like-for-like periods when the latest year is incomplete. | `yyyy-mm-dd` |
| **Revenue PY** | Revenue in the same period one year earlier (like-for-like). |  | `"R$" #,0` |
| **Orders PY** | Orders in the same period one year earlier (like-for-like). |  | `#,0` |
| **Late Delivery Rate PY** | Late Delivery Rate in the same period one year earlier (like-for-like). |  | `0.0%` |
| **Avg Review Score PY** | Avg Review Score in the same period one year earlier (like-for-like). |  | `0.00` |
| **Revenue YoY %** | Year-over-year change in revenue. | Growth KPI for the executive page. | `+0.0%;-0.0%;0.0%` |
| **Orders YoY %** | Year-over-year change in orders. |  | `+0.0%;-0.0%;0.0%` |
| **Late Delivery Rate YoY (pp)** | Change in late rate vs last year, in percentage points (a rate is compared by subtraction, not division). |  | `+0.0" pp";-0.0" pp";0.0" pp"` |
| **Avg Review Score YoY** | Change in average review score vs last year. |  | `+0.00;-0.00;0.00` |
| **Revenue PM** | Revenue in the previous month. |  | `"R$" #,0` |
| **Revenue MoM %** | Month-over-month change in revenue. |  | `+0.0%;-0.0%;0.0%` |
| **Revenue YTD** | Revenue from 1 January to the end of the selected period. |  | `"R$" #,0` |
| **Revenue Rolling 3M** | Revenue in the three months up to the end of the selected period. Smooths monthly noise. |  | `"R$" #,0` |

## Customers

| Measure | Definition | Why it matters | Format |
|---|---|---|---|
| **Repeat Customers** | Customers with two or more orders in the selected period. |  | `#,0` |
| **Repeat Customer Rate** | Repeat Customers / Active Customers. | Retention health. Very low here (about 3%). | `0.0%` |
| **New Customers** | Customers whose first purchase falls in the selected period. |  | `#,0` |
| **Repeat Order Share** | Share of (non-canceled) orders placed by a customer who had bought before. |  | `0.0%` |

## Delivery

| Measure | Definition | Why it matters | Format |
|---|---|---|---|
| **All Orders** | Every order placed, including canceled and unavailable ones. |  | `#,0` |
| **Canceled Orders** | Orders with status canceled or unavailable. |  | `#,0` |
| **Cancellation Rate** | Canceled Orders / All Orders. |  | `0.0%` |
| **Delivered Orders** | Orders delivered to the customer (status delivered with a delivery date). |  | `#,0` |
| **Late Orders** | Delivered orders that arrived after the estimated delivery date. |  | `#,0` |
| **Late Delivery Rate** | Late Orders / Delivered Orders. | The KPI most strongly linked to bad reviews. | `0.0%` |
| **On-Time Delivery Rate** | 1 - Late Delivery Rate. |  | `0.0%` |
| **Avg Delivery Days** | Average days from purchase to delivery. |  | `0.0` |
| **Avg Promised Days** | Average days between purchase and the estimated delivery date shown at checkout (delivered orders). |  | `0.0` |
| **Avg Days vs Estimate** | Average of delivered date minus estimated date. Negative = arrived early. | Shows how much safety buffer the delivery promise has. | `+0.0;-0.0;0.0` |
| **Avg Days Late (Late Orders)** | How late late orders are, on average. |  | `0.0` |
| **Orders Delivered (by Delivery Date)** | Delivered orders counted by the date they arrived instead of the date they were bought. | Warehouse and carrier workload view. | `#,0` |

## Satisfaction

| Measure | Definition | Why it matters | Format |
|---|---|---|---|
| **Reviews** | Orders with a review. |  | `#,0` |
| **Avg Review Score** | Average 1-5 star score. | Headline customer satisfaction KPI. | `0.00` |
| **Bad Review Rate** | Share of reviews with 1 or 2 stars. | More sensitive to problems than the average score. | `0.0%` |
| **Five-Star Rate** | Share of reviews with 5 stars. |  | `0.0%` |
| **Avg Review - On Time** | Average score of on-time orders. |  | `0.00` |
| **Avg Review - Late** | Average score of late orders. |  | `0.00` |
| **Review Gap On Time vs Late** | How many stars a late delivery costs. | Quantifies the cost of late delivery in one number. | `0.00` |

## Sellers and products

| Measure | Definition | Why it matters | Format |
|---|---|---|---|
| **Seller Revenue Rank** | Rank of the seller by revenue within the current selection. |  | `0` |
| **Top 10% Sellers Revenue Share** | Share of revenue generated by the top 10% of active sellers. | Concentration risk: how dependent the business is on a few sellers. | `0.0%` |
| **Late Delivery Rate (Product View)** | Late Delivery Rate for orders containing the selected products or categories. | Lets order-level KPIs be sliced by product without a bidirectional relationship. | `0.0%` |
| **Bad Review Rate (Product View)** | Bad Review Rate for orders containing the selected products or categories. | Lets order-level KPIs be sliced by product without a bidirectional relationship. | `0.0%` |
| **Avg Review Score (Product View)** | Avg Review Score for orders containing the selected products or categories. | Lets order-level KPIs be sliced by product without a bidirectional relationship. | `0.00` |

## Delivery risk model

| Measure | Definition | Why it matters | Format |
|---|---|---|---|
| **Scored Orders** | Test-period orders (Jun-Aug 2018) scored by the model. |  | `#,0` |
| **Actual Late Rate (Scored)** | Late rate among scored orders. |  | `0.0%` |
| **Avg Risk Score** | Average model score (a relative risk score, see notebook 02). |  | `0.0%` |
| **Late Rate Lift vs Average** | How many times more often orders in this risk group are late than the average scored order. |  | `0.0"x"` |
| **Share of Late Orders Caught** | Share of all late orders that fall in the selected risk band or decile. |  | `0.0%` |
| **Cumulative Late Orders Caught** | Gains-curve value for the current decile. | Shows how much of the problem the model catches for a given review effort. | `0.0%` |

## Labels

| Measure | Definition | Why it matters | Format |
|---|---|---|---|
| **Selected Period** | Text such as 'Jan 2017 - Aug 2018' for dynamic titles. |  | text |
| **Revenue YoY Label** | Subtitle text for the revenue card. |  | text |
| **Late Rate Color** | Green up to 5% late, amber up to 10%, red above. |  | text |
