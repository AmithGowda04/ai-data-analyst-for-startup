"""Run all raw loads in dependency order and record row counts."""
import datetime
import time
import uuid

from google.cloud import bigquery

import load_ad_spend
import load_raw
from load_raw import RAW, count_rows, get_client

TABLES = ["orders", "order_items", "users", "products", "events", "ad_spend"]
LOG_TABLE = f"{RAW}.load_log"
LOG_SCHEMA = [
    bigquery.SchemaField("run_id", "STRING"),
    bigquery.SchemaField("run_ts", "TIMESTAMP"),
    bigquery.SchemaField("table_name", "STRING"),
    bigquery.SchemaField("row_count", "INT64"),
    bigquery.SchemaField("run_seconds", "FLOAT64"),
]


def record_counts(elapsed=None):
    c = get_client()
    run_id = uuid.uuid4().hex[:8]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows = [
        {"run_id": run_id, "run_ts": now, "table_name": t,
         "row_count": count_rows(c, f"{RAW}.{t}"), "run_seconds": elapsed}
        for t in TABLES
    ]
    cfg = bigquery.LoadJobConfig(schema=LOG_SCHEMA, write_disposition="WRITE_APPEND")
    c.load_table_from_json(rows, LOG_TABLE, job_config=cfg).result()
    return run_id, rows


def main():
    t0 = time.time()
    load_raw.main()        # orders and users must exist before ad spend
    load_ad_spend.main()
    elapsed = round(time.time() - t0, 1)
    run_id, rows = record_counts(elapsed)
    print(f"\nrun {run_id} finished in {elapsed}s")
    for r in rows:
        print(f"  {r['table_name']:<12} {r['row_count']:>12,}")


if __name__ == "__main__":
    main()