"""
Build a Power BI-ready star schema from the raw Olist e-commerce tables.

Input : data/raw/*.csv          (9 relational tables exported from Olist's transactional system)
Output: data/processed/*.csv    (2 fact tables + 4 dimension tables)

    FactOrderItems  grain = one row per item in an order      -> revenue, product and seller analysis
    FactOrders      grain = one row per order                 -> delivery, satisfaction, payment, retention KPIs
    DimDate         one row per calendar day 2017-01-01 .. 2018-12-31
    DimCustomer     one row per real person (customer_unique_id, not customer_id)
    DimProduct      one row per product, English category names
    DimSeller       one row per seller

Run:  python src/build_star_schema.py
"""
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

# 2016 has only ~330 orders spread over 3 months and Sep/Oct 2018 only 20 (mostly canceled),
# so the analysis window is the 20 complete months in between.
WINDOW_START = pd.Timestamp("2017-01-01")
WINDOW_END = pd.Timestamp("2018-09-01")  # exclusive

# Orders with these statuses never turned into a sale, so they are kept in FactOrders
# (to measure cancellations) but excluded from FactOrderItems (revenue).
NON_SALE_STATUSES = {"canceled", "unavailable"}

BRAZIL_REGIONS = {
    "North": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "Northeast": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Central-West": ["DF", "GO", "MT", "MS"],
    "Southeast": ["ES", "MG", "RJ", "SP"],
    "South": ["PR", "RS", "SC"],
}
STATE_TO_REGION = {state: region for region, states in BRAZIL_REGIONS.items() for state in states}

# Two categories in the product table have no row in the translation file.
MISSING_TRANSLATIONS = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_and_food_preparers",
}


def load_raw() -> dict[str, pd.DataFrame]:
    date_cols = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    return {
        "orders": pd.read_csv(RAW / "olist_orders_dataset.csv", parse_dates=date_cols),
        "items": pd.read_csv(RAW / "olist_order_items_dataset.csv"),
        "payments": pd.read_csv(RAW / "olist_order_payments_dataset.csv"),
        "reviews": pd.read_csv(
            RAW / "olist_order_reviews_dataset.csv",
            parse_dates=["review_creation_date", "review_answer_timestamp"],
        ),
        "customers": pd.read_csv(RAW / "olist_customers_dataset.csv", dtype={"customer_zip_code_prefix": str}),
        "products": pd.read_csv(RAW / "olist_products_dataset.csv"),
        "sellers": pd.read_csv(RAW / "olist_sellers_dataset.csv", dtype={"seller_zip_code_prefix": str}),
        "geo": pd.read_csv(RAW / "olist_geolocation_dataset.csv", dtype={"geolocation_zip_code_prefix": str}),
        "translation": pd.read_csv(RAW / "product_category_name_translation.csv", encoding="utf-8-sig"),
    }


def surrogate_key(values: pd.Series) -> pd.Series:
    """Map long hash IDs to small integers (1..n). Integer keys compress far better in Power BI."""
    uniques = np.sort(values.dropna().unique())
    return pd.Series(np.arange(1, len(uniques) + 1), index=uniques)


def clean_city(name) -> str:
    """
    Seller cities are free text: 'sao paulo - sp', 'maua/sao paulo', even an e-mail address.
    Keep the part before any separator, strip accents, and mark values that are clearly not a city as Unknown.
    """
    if not isinstance(name, str):
        return "Unknown"
    name = re.split(r"[,/\\]| - ", name.replace("\u00b4", "'"))[0]
    ascii_name = " ".join(unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().split())
    if not ascii_name or re.search(r"[0-9@]", ascii_name) or len(ascii_name) <= 2:
        return "Unknown"
    return ascii_name.title()


# Readable labels for the largest categories; the rest are formatted generically.
CATEGORY_LABELS = {
    "health_beauty": "Health & beauty",
    "watches_gifts": "Watches & gifts",
    "bed_bath_table": "Bed bath & table",
    "sports_leisure": "Sports & leisure",
    "computers_accessories": "Computers & accessories",
    "furniture_decor": "Furniture & decor",
    "cool_stuff": "Cool stuff",
    "garden_tools": "Garden tools",
    "baby": "Baby",
    "toys": "Toys",
    "telephony": "Telephony",
    "perfumery": "Perfumery",
    "office_furniture": "Office furniture",
    "consoles_games": "Consoles & games",
    "fashion_bags_accessories": "Fashion bags & accessories",
    "small_appliances": "Small appliances",
    "home_appliances": "Home appliances",
    "home_construction": "Home construction",
}


def pretty_category(name: str) -> str:
    return CATEGORY_LABELS.get(name, name.replace("_", " ").strip().capitalize())


def zip_centroids(geo: pd.DataFrame) -> pd.DataFrame:
    """One lat/lng per 5-digit zip prefix. Drops points outside Brazil's bounding box (bad geocodes)."""
    g = geo.rename(
        columns={"geolocation_zip_code_prefix": "zip", "geolocation_lat": "lat", "geolocation_lng": "lng"}
    )
    g["zip"] = g["zip"].str.zfill(5)
    in_brazil = g["lat"].between(-34, 6) & g["lng"].between(-74, -34)
    return g[in_brazil].groupby("zip")[["lat", "lng"]].median()


def haversine_km(lat1, lng1, lat2, lng2):
    lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def build() -> dict[str, pd.DataFrame]:
    raw = load_raw()
    orders = raw["orders"]
    orders = orders[
        (orders["order_purchase_timestamp"] >= WINDOW_START) & (orders["order_purchase_timestamp"] < WINDOW_END)
    ].copy()

    # ---------------------------------------------------------------- customers
    # customer_id is created per order; customer_unique_id identifies the person.
    # Using customer_id would make every customer look like a one-time buyer.
    customers = raw["customers"].copy()
    customers["customer_zip_code_prefix"] = customers["customer_zip_code_prefix"].str.zfill(5)
    orders = orders.merge(customers, on="customer_id", how="left")
    cust_key = surrogate_key(orders["customer_unique_id"])
    orders["CustomerKey"] = orders["customer_unique_id"].map(cust_key)

    # A person can order from different addresses: keep the location of their most recent order.
    latest = orders.sort_values("order_purchase_timestamp").drop_duplicates("customer_unique_id", keep="last")
    first_order = orders.groupby("customer_unique_id")["order_purchase_timestamp"].min().dt.normalize()
    dim_customer = pd.DataFrame(
        {
            "CustomerKey": latest["CustomerKey"].values,
            "CustomerUniqueID": latest["customer_unique_id"].values,
            "City": latest["customer_city"].map(clean_city).values,
            "State": latest["customer_state"].values,
            "Region": latest["customer_state"].map(STATE_TO_REGION).values,
            "ZipPrefix": latest["customer_zip_code_prefix"].values,
            "FirstOrderDate": latest["customer_unique_id"].map(first_order).dt.date.values,
        }
    ).sort_values("CustomerKey")

    # ---------------------------------------------------------------- products
    translation = dict(zip(raw["translation"]["product_category_name"], raw["translation"]["product_category_name_english"]))
    translation.update(MISSING_TRANSLATIONS)
    products = raw["products"].copy()
    prod_key = surrogate_key(products["product_id"])
    english = products["product_category_name"].map(translation).fillna("unknown")
    volume_cm3 = products["product_length_cm"] * products["product_height_cm"] * products["product_width_cm"]
    dim_product = pd.DataFrame(
        {
            "ProductKey": products["product_id"].map(prod_key).values,
            "ProductID": products["product_id"].values,
            "Category": english.map(pretty_category).values,
            "CategoryPortuguese": products["product_category_name"].fillna("desconhecido").values,
            "WeightG": products["product_weight_g"].values,
            "VolumeCm3": volume_cm3.values,
            "PhotoCount": products["product_photos_qty"].values,
        }
    ).sort_values("ProductKey")

    # ---------------------------------------------------------------- sellers
    sellers = raw["sellers"].copy()
    sellers["seller_zip_code_prefix"] = sellers["seller_zip_code_prefix"].str.zfill(5)
    seller_key = surrogate_key(sellers["seller_id"])
    dim_seller = pd.DataFrame(
        {
            "SellerKey": sellers["seller_id"].map(seller_key).values,
            "SellerID": sellers["seller_id"].values,
            # Seller names are anonymised in the source data; a short readable label for report tables.
            "SellerName": sellers["seller_id"].map(seller_key).map(lambda k: f"Seller {k:04d}").values,
            "City": sellers["seller_city"].map(clean_city).values,
            "State": sellers["seller_state"].values,
            "Region": sellers["seller_state"].map(STATE_TO_REGION).values,
            "ZipPrefix": sellers["seller_zip_code_prefix"].values,
        }
    ).sort_values("SellerKey")

    # ---------------------------------------------------------------- order keys
    order_key = surrogate_key(orders["order_id"])
    orders["OrderKey"] = orders["order_id"].map(order_key)
    orders["OrderDate"] = orders["order_purchase_timestamp"].dt.normalize()

    # ---------------------------------------------------------------- items (grain: order line)
    items = raw["items"].merge(
        orders[["order_id", "OrderKey", "OrderDate", "CustomerKey", "order_status"]], on="order_id", how="inner"
    )
    items["ProductKey"] = items["product_id"].map(prod_key)
    items["SellerKey"] = items["seller_id"].map(seller_key)
    sale_items = items[~items["order_status"].isin(NON_SALE_STATUSES)]
    fact_items = sale_items.rename(
        columns={"order_item_id": "OrderItemNumber", "price": "Price", "freight_value": "Freight"}
    )[["OrderKey", "OrderItemNumber", "OrderDate", "CustomerKey", "ProductKey", "SellerKey", "Price", "Freight"]]
    fact_items = fact_items.sort_values(["OrderKey", "OrderItemNumber"])

    # ---------------------------------------------------------------- order-level item summary
    items = items.merge(dim_product[["ProductKey", "WeightG", "VolumeCm3"]], on="ProductKey", how="left")
    order_items = items.groupby("order_id").agg(
        ItemCount=("order_item_id", "size"),
        SellerCount=("seller_id", "nunique"),
        ProductValue=("price", "sum"),
        FreightValue=("freight_value", "sum"),
        TotalWeightG=("WeightG", "sum"),
    )
    # Primary seller = the seller with the largest share of the order value (98.7% of orders have one seller).
    seller_value = items.groupby(["order_id", "seller_id"])["price"].sum().reset_index()
    primary_seller = seller_value.sort_values("price").drop_duplicates("order_id", keep="last").set_index("order_id")["seller_id"]
    order_items["SellerKey"] = primary_seller.map(seller_key)

    # Seller-to-customer distance (max over sellers in the order).
    centroids = zip_centroids(raw["geo"])
    items = items.merge(sellers[["seller_id", "seller_zip_code_prefix"]], on="seller_id", how="left")
    items = items.merge(orders[["order_id", "customer_zip_code_prefix"]], on="order_id", how="left")
    s_ll = centroids.reindex(items["seller_zip_code_prefix"]).to_numpy()
    c_ll = centroids.reindex(items["customer_zip_code_prefix"]).to_numpy()
    items["distance_km"] = haversine_km(s_ll[:, 0], s_ll[:, 1], c_ll[:, 0], c_ll[:, 1])
    order_items["DistanceKm"] = items.groupby("order_id")["distance_km"].max().round(1)

    # ---------------------------------------------------------------- payments
    pay = raw["payments"]
    pay_type = (
        pay.groupby(["order_id", "payment_type"])["payment_value"].sum().reset_index()
        .sort_values("payment_value").drop_duplicates("order_id", keep="last").set_index("order_id")["payment_type"]
    )
    order_pay = pay.groupby("order_id").agg(PaymentValue=("payment_value", "sum"), Installments=("payment_installments", "max"))
    order_pay["PaymentType"] = pay_type.str.replace("_", " ").str.capitalize()

    # ---------------------------------------------------------------- reviews
    # 547 orders have more than one review: keep the most recent answer.
    reviews = (
        raw["reviews"].sort_values("review_answer_timestamp")
        .drop_duplicates("order_id", keep="last").set_index("order_id")
    )

    # ---------------------------------------------------------------- FactOrders (grain: order)
    f = orders.set_index("order_id").join(order_items).join(order_pay).join(reviews[["review_score"]])
    f["IsCanceled"] = f["order_status"].isin(NON_SALE_STATUSES).astype(int)

    delivered = (f["order_status"] == "delivered") & f["order_delivered_customer_date"].notna()
    f["IsDelivered"] = delivered.astype(int)
    f["DeliveredDate"] = f["order_delivered_customer_date"].dt.normalize().where(delivered)
    f["EstimatedDate"] = f["order_estimated_delivery_date"].dt.normalize()
    f["PromisedDays"] = (f["EstimatedDate"] - f["OrderDate"]).dt.days
    f["DeliveryDays"] = ((f["order_delivered_customer_date"] - f["order_purchase_timestamp"]).dt.total_seconds() / 86400).where(delivered).round(1)
    # The estimate is a calendar date, so lateness is compared at date level:
    # an order delivered any time on the estimated day counts as on time.
    f["DelayDays"] = (f["DeliveredDate"] - f["EstimatedDate"]).dt.days
    f["IsLate"] = np.where(delivered, (f["DelayDays"] > 0).astype(float), np.nan)
    f["DeliveryStatus"] = np.select(
        [~delivered, f["DelayDays"] > 0], ["Not delivered", "Late"], default="On time"
    )
    # Buckets for the "review score vs. delay" chart. DelayBucketSort is used with
    # Power BI's "Sort by column" so the buckets appear in logical order.
    buckets = [
        (-np.inf, -15, "15+ days early"), (-14, -8, "8-14 days early"), (-7, -1, "1-7 days early"),
        (0, 0, "On the estimated day"), (1, 3, "1-3 days late"), (4, 7, "4-7 days late"), (8, np.inf, "8+ days late"),
    ]
    f["DelayBucket"], f["DelayBucketSort"] = "Not delivered", 99
    for sort, (lo, hi, label) in enumerate(buckets, start=1):
        in_bucket = delivered & f["DelayDays"].between(lo, hi)
        f.loc[in_bucket, "DelayBucket"] = label
        f.loc[in_bucket, "DelayBucketSort"] = sort

    f["ReviewScore"] = f["review_score"]
    f["IsBadReview"] = np.where(f["ReviewScore"].notna(), (f["ReviewScore"] <= 2).astype(float), np.nan)

    # Order sequence per customer (cancelled orders do not count as purchases).
    sales = f[f["IsCanceled"] == 0].sort_values("order_purchase_timestamp")
    f["CustomerOrderNumber"] = sales.groupby("CustomerKey").cumcount().add(1)
    f["IsRepeatOrder"] = np.where(f["CustomerOrderNumber"].notna(), (f["CustomerOrderNumber"] > 1).astype(float), np.nan)

    f = f.reset_index().rename(columns={"order_id": "OrderID", "order_status": "OrderStatus"})
    f["OrderStatus"] = f["OrderStatus"].str.capitalize()
    f["PurchaseHour"] = f["order_purchase_timestamp"].dt.hour
    fact_orders = f[
        [
            "OrderKey", "OrderID", "OrderDate", "PurchaseHour", "CustomerKey", "SellerKey", "OrderStatus", "IsCanceled",
            "ItemCount", "SellerCount", "ProductValue", "FreightValue", "PaymentValue", "PaymentType", "Installments",
            "TotalWeightG", "DistanceKm", "IsDelivered", "DeliveredDate", "EstimatedDate", "PromisedDays",
            "DeliveryDays", "DelayDays", "IsLate", "DeliveryStatus", "DelayBucket", "DelayBucketSort",
            "ReviewScore", "IsBadReview",
            "CustomerOrderNumber", "IsRepeatOrder",
        ]
    ].sort_values("OrderKey")
    for col in ["SellerKey", "ItemCount", "SellerCount", "Installments", "PromisedDays", "DelayDays",
                "IsLate", "ReviewScore", "IsBadReview", "CustomerOrderNumber", "IsRepeatOrder"]:
        fact_orders[col] = fact_orders[col].astype("Int64")

    # ---------------------------------------------------------------- DimDate
    # Full calendar years are required for Power BI time intelligence (SAMEPERIODLASTYEAR, YTD).
    dates = pd.date_range("2017-01-01", "2018-12-31", freq="D")
    dim_date = pd.DataFrame(
        {
            "Date": dates,
            "Year": dates.year,
            "Quarter": "Q" + dates.quarter.astype(str),
            "MonthNumber": dates.month,
            "Month": dates.strftime("%b"),
            "YearMonth": dates.strftime("%Y-%m"),
            "MonthStart": dates.to_period("M").to_timestamp(),
            "WeekStart": (dates - pd.to_timedelta(dates.weekday, unit="D")),
            "DayOfWeekNumber": dates.weekday + 1,
            "DayOfWeek": dates.strftime("%a"),
            "IsWeekend": (dates.weekday >= 5).astype(int),
            "IsInDataWindow": ((dates >= WINDOW_START) & (dates < WINDOW_END)).astype(int),
        }
    )

    return {
        "FactOrderItems": fact_items,
        "FactOrders": fact_orders,
        "DimDate": dim_date,
        "DimCustomer": dim_customer,
        "DimProduct": dim_product,
        "DimSeller": dim_seller,
    }


def validate(tables: dict[str, pd.DataFrame]) -> None:
    """Basic integrity checks: unique dimension keys and no orphan foreign keys."""
    checks = [
        ("DimCustomer", "CustomerKey"), ("DimProduct", "ProductKey"),
        ("DimSeller", "SellerKey"), ("DimDate", "Date"), ("FactOrders", "OrderKey"),
    ]
    for table, key in checks:
        assert tables[table][key].is_unique, f"{table}.{key} is not unique"

    fo, fi = tables["FactOrders"], tables["FactOrderItems"]
    assert fi["CustomerKey"].isin(tables["DimCustomer"]["CustomerKey"]).all()
    assert fi["ProductKey"].isin(tables["DimProduct"]["ProductKey"]).all()
    assert fi["SellerKey"].isin(tables["DimSeller"]["SellerKey"]).all()
    assert fi["OrderKey"].isin(fo["OrderKey"]).all()
    assert fo["CustomerKey"].isin(tables["DimCustomer"]["CustomerKey"]).all()
    assert fo["SellerKey"].dropna().isin(tables["DimSeller"]["SellerKey"]).all()
    assert fo["OrderDate"].isin(tables["DimDate"]["Date"]).all()
    assert fo["DeliveredDate"].dropna().isin(tables["DimDate"]["Date"]).all()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tables = build()
    validate(tables)
    for name, df in tables.items():
        df.to_csv(OUT / f"{name}.csv", index=False, date_format="%Y-%m-%d", encoding="utf-8-sig")
        print(f"{name:<16}{len(df):>9,} rows  {df.shape[1]:>3} cols")
    print(f"\nWritten to {OUT}")


if __name__ == "__main__":
    main()
