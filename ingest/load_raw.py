"""Idempotent raw loads: thelook -> <project>.raw (sandbox-safe, no DML)."""
import datetime
import logging
import os
import time

from dotenv import load_dotenv
from google.api_core.exceptions import NotFound
from google.cloud import bigquery
from google.oauth2 import service_account

load_dotenv()
PROJECT = os.environ["GCP_PROJECT_ID"]
LOCATION = "US"  # must match the public dataset's location
SRC = "bigquery-public-data.thelook_ecommerce"
RAW = f"{PROJECT}.raw"
START = datetime.date(2024, 1, 1)
MAX_BYTES = 5 * 1024**3  # billing cap per job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ingest")

USER_PII = "first_name, last_name, email, street_address, latitude, longitude, user_geom"

# Full-refresh tables: small and mutable. Only complete days (< today, UTC).
FULL_REFRESH = {
    "orders": f"SELECT * FROM `{SRC}.orders` "
              "WHERE DATE(created_at) >= @lo AND DATE(created_at) < @hi",
    "order_items": f"SELECT * FROM `{SRC}.order_items` "
                   "WHERE DATE(created_at) >= @lo AND DATE(created_at) < @hi",
    "users": f"SELECT * EXCEPT ({USER_PII}) FROM `{SRC}.users`",
    "products": f"SELECT * FROM `{SRC}.products`",
}


def get_client() -> bigquery.Client:
    creds = service_account.Credentials.from_service_account_file(os.environ["LOADER_KEY_PATH"])
    return bigquery.Client(project=PROJECT, credentials=creds, location=LOCATION)


def count_rows(c: bigquery.Client, table: str) -> int:
    try:
        return list(c.query(f"SELECT COUNT(*) AS n FROM `{table}`").result())[0].n
    except NotFound:
        return 0


def run_query(c, sql, table, disposition, params):
    cfg = bigquery.QueryJobConfig(
        destination=table,
        write_disposition=disposition,
        maximum_bytes_billed=MAX_BYTES,
        query_parameters=params,
    )
    job = c.query(sql, job_config=cfg)
    job.result()
    return job.total_bytes_billed or 0


def date_params(lo: datetime.date, hi: datetime.date):
    return [
        bigquery.ScalarQueryParameter("lo", "DATE", lo),
        bigquery.ScalarQueryParameter("hi", "DATE", hi),
    ]


def last_loaded_date(c, table):
    try:
        return list(c.query(f"SELECT MAX(DATE(created_at)) AS d FROM `{table}`").result())[0].d
    except NotFound:
        return None


def load_full(c, name, sql, today):
    table = f"{RAW}.{name}"
    before = count_rows(c, table)
    t0 = time.time()
    billed = run_query(c, sql, table, "WRITE_TRUNCATE", date_params(START, today))
    after = count_rows(c, table)
    log.info("%-12s mode=replace rows %s -> %s billed=%.1f MB (%.1fs)",
             name, f"{before:,}", f"{after:,}", billed / 1e6, time.time() - t0)


def load_events(c, today):
    table = f"{RAW}.events"
    last = last_loaded_date(c, table)
    lo = START if last is None else last + datetime.timedelta(days=1)
    before = count_rows(c, table)
    if lo >= today:
        log.info("%-12s mode=append rows %s -> %s (nothing new, loaded through %s)",
                 "events", f"{before:,}", f"{before:,}", last)
        return
    sql = (f"SELECT * EXCEPT (ip_address) FROM `{SRC}.events` "
           "WHERE DATE(created_at) >= @lo AND DATE(created_at) < @hi")
    disposition = "WRITE_TRUNCATE" if last is None else "WRITE_APPEND"
    t0 = time.time()
    billed = run_query(c, sql, table, disposition, date_params(lo, today))
    after = count_rows(c, table)
    log.info("%-12s mode=append rows %s -> %s billed=%.1f MB (%.1fs) window=[%s, %s)",
             "events", f"{before:,}", f"{after:,}", billed / 1e6, time.time() - t0, lo, today)


def main():
    c = get_client()
    ds = bigquery.Dataset(RAW)
    ds.location = LOCATION
    c.create_dataset(ds, exists_ok=True)
    today = datetime.datetime.now(datetime.timezone.utc).date()
    for name, sql in FULL_REFRESH.items():
        load_full(c, name, sql, today)
    load_events(c, today)


if __name__ == "__main__":
    main()