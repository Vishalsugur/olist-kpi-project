"""
Run every query in sql/kpi_queries.sql with DuckDB and print the results.

    pip install duckdb
    python src/run_sql.py
"""
import os
import re
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)  # the views read data/processed/*.csv with relative paths

sql = (ROOT / "sql" / "kpi_queries.sql").read_text()
con = duckdb.connect()

# Split on ";" at the end of a line, keeping the "-- Qn." title of each query.
for statement in [s.strip() for s in re.split(r";\s*\n", sql) if s.strip()]:
    title = re.search(r"^-- (Q\d+\..*)$", statement, flags=re.M)
    body = "\n".join(line for line in statement.splitlines() if not line.strip().startswith("--")).strip()
    if not body:
        continue
    result = con.sql(body)
    if title:
        print(f"\n{title.group(1)}")
        print(result.df().to_string(index=False))
