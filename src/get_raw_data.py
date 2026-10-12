"""
Download the raw Olist tables (about 120 MB) from Olist's public GitHub repository into data/raw/.

    python src/get_raw_data.py

Source: https://github.com/olist/work-at-olist-data (MIT licence).
The same data is on Kaggle as "Brazilian E-Commerce Public Dataset by Olist".
"""
import urllib.request
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/"
FILES = [
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        target = RAW / name
        if target.exists() and target.stat().st_size > 0:
            print(f"already there  {name}")
            continue
        print(f"downloading    {name} ...", end=" ", flush=True)
        urllib.request.urlretrieve(BASE_URL + name, target)
        print(f"{target.stat().st_size / 1e6:.1f} MB")
    print(f"\nRaw data ready in {RAW}")


if __name__ == "__main__":
    main()
