"""
Build a single, dashboard-ready table for the Power BI service (browser version).

The browser version of Power BI makes multi-table modeling awkward, so this script joins the star schema
into ONE flat table: one row per sold order, with the customer location, main product category,
delivery and review fields already attached. Percent KPIs are stored as 0/100 so that "Average" in a
visual directly shows the percentage (e.g. Late % average = 6.8).

Input : data/processed/*.csv   (run build_star_schema.py first)
Output: olist_dashboard_data.csv   (repository root; Power BI in the browser loads it from its raw GitHub URL,
                                    so keep the file name and location unchanged)

Run:  python src/build_dashboard_table.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
OUT_CSV = ROOT / "olist_dashboard_data.csv"


def build() -> pd.DataFrame:
    orders = pd.read_csv(P / "FactOrders.csv", parse_dates=["OrderDate"])
    items = pd.read_csv(P / "FactOrderItems.csv")
    customers = pd.read_csv(P / "DimCustomer.csv")
    products = pd.read_csv(P / "DimProduct.csv")

    # Sold orders only (orders with at least one sold item): matches the Revenue/Orders KPIs of the project.
    df = orders[orders["OrderKey"].isin(items["OrderKey"])].copy()
    df = df.merge(customers[["CustomerKey", "State", "Region"]], on="CustomerKey", how="left")

    # Main category = category of the most expensive item in the order
    main = items.sort_values("Price").drop_duplicates("OrderKey", keep="last")[["OrderKey", "ProductKey"]]
    main = main.merge(products[["ProductKey", "Category"]], on="ProductKey")[["OrderKey", "Category"]]
    df = df.merge(main, on="OrderKey", how="left")

    # Number prefixes make the buckets sort in the right order without any extra setup.
    order_labels = {1: "1) 15+ days early", 2: "2) 8-14 days early", 3: "3) 1-7 days early", 4: "4) On the estimated day",
                    5: "5) 1-3 days late", 6: "6) 4-7 days late", 7: "7) 8+ days late", 99: "8) Not delivered yet"}

    def pct(flag: pd.Series) -> pd.Series:
        return (flag * 100).round().astype("Int64")

    out = pd.DataFrame(
        {
            "Order ID": df["OrderID"],
            "Order Date": df["OrderDate"],
            "Year": df["OrderDate"].dt.year.astype(str),
            "Year-Month": df["OrderDate"].dt.strftime("%Y-%m"),
            "Customer State": df["State"],
            "Customer Region": df["Region"],
            "Main Category": df["Category"],
            "Payment Type": df["PaymentType"],
            "Revenue": df["ProductValue"].round(2),
            "Freight": df["FreightValue"].round(2),
            "Items": df["ItemCount"].astype("Int64"),
            "Delivery Status": df["DeliveryStatus"],
            "Delivery Timing": df["DelayBucketSort"].map(order_labels),
            "Delivery Days": df["DeliveryDays"],
            "Promised Days": df["PromisedDays"],
            "Late %": pct(df["IsLate"]),
            "On-Time %": pct(1 - df["IsLate"]),
            "Review Score": df["ReviewScore"].astype("Int64"),
            "Bad Review %": pct(df["IsBadReview"]),
            "Repeat Order %": pct(df["IsRepeatOrder"]),
        }
    ).sort_values("Order Date")
    return out


def main() -> None:
    df = build()
    # Whole numbers are written without ".0" so no locale can misread them; only money and days keep decimals.
    df.to_csv(OUT_CSV, index=False, date_format="%Y-%m-%d", encoding="utf-8")
    print(f"{len(df):,} orders written to {OUT_CSV}")
    print("Expected card values:")
    print(f"  Revenue (sum)          R$ {df['Revenue'].sum():,.2f}")
    print(f"  Orders (count)         {df['Order ID'].nunique():,}")
    print(f"  Avg order value        R$ {df['Revenue'].mean():,.2f}")
    print(f"  Late % (average)       {df['Late %'].mean():.2f}")
    print(f"  On-Time % (average)    {df['On-Time %'].mean():.2f}")
    print(f"  Review score (average) {df['Review Score'].mean():.2f}")
    print(f"  Bad Review % (average) {df['Bad Review %'].mean():.2f}")


if __name__ == "__main__":
    main()
