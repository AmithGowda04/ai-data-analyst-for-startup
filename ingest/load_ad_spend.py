"""Synthetic ad spend -> raw.ad_spend. Deterministic, incremental, sandbox-safe."""
import datetime
import hashlib
import logging
import random

from google.cloud import bigquery
from google.api_core.exceptions import NotFound

from load_raw import PROJECT, RAW, START, count_rows, get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ad_spend")

# channel -> (target cost per order $, cost per click $, click-through rate)
# Names match users.traffic_source. Organic has no paid spend.
CHANNELS = {
    "Search":   (18.0, 1.20, 0.040),
    "Facebook": (24.0, 0.80, 0.020),
    "Display":  (30.0, 0.50, 0.010),
    "Email":    (4.0, 0.10, 0.060),
}

SCHEMA = [
    bigquery.SchemaField("date", "DATE"),
    bigquery.SchemaField("channel", "STRING"),
    bigquery.SchemaField("spend", "FLOAT64"),
    bigquery.SchemaField("impressions", "INT64"),
    bigquery.SchemaField("clicks", "INT64"),
    bigquery.SchemaField("conversions", "INT64"),
]


def rng_for(day: datetime.date, channel: str) -> random.Random:
    seed = int(hashlib.sha256(f"{day}|{channel}".encode()).hexdigest()[:8], 16)
    return random.Random(seed)  # same inputs -> same numbers, every run


def last_loaded(c, table):
    try:
        return list(c.query(f"SELECT MAX(date) AS d FROM `{table}`").result())[0].d
    except NotFound:
        return None


def orders_by_day_channel(c, lo, hi):
    sql = f"""
        SELECT DATE(o.created_at) AS d, u.traffic_source AS channel, COUNT(*) AS orders
        FROM `{RAW}.orders` o JOIN `{RAW}.users` u ON o.user_id = u.id
        WHERE DATE(o.created_at) >= @lo AND DATE(o.created_at) < @hi
        GROUP BY 1, 2
    """
    cfg = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("lo", "DATE", lo),
        bigquery.ScalarQueryParameter("hi", "DATE", hi),
    ])
    return {(r.d, r.channel): r.orders for r in c.query(sql, job_config=cfg).result()}


def build_rows(c, lo, hi):
    orders = orders_by_day_channel(c, lo, hi)
    rows, day = [], lo
    while day < hi:
        for channel, (cpa, cpc, ctr) in CHANNELS.items():
            r = rng_for(day, channel)
            n = orders.get((day, channel), 0)
            spend = round(cpa * (n + 2) * r.uniform(0.75, 1.25), 2)
            clicks = int(spend / cpc * r.uniform(0.9, 1.1))
            rows.append({
                "date": day.isoformat(),
                "channel": channel,
                "spend": spend,
                "impressions": int(clicks / ctr * r.uniform(0.9, 1.1)),
                "clicks": clicks,
                "conversions": int(round(n * r.uniform(0.85, 1.15))),
            })
        day += datetime.timedelta(days=1)
    return rows


def main():
    c = get_client()
    table = f"{RAW}.ad_spend"
    today = datetime.datetime.now(datetime.timezone.utc).date()
    last = last_loaded(c, table)
    lo = START if last is None else last + datetime.timedelta(days=1)
    before = count_rows(c, table)
    if lo >= today:
        log.info("ad_spend mode=append rows %s -> %s (nothing new, loaded through %s)",
                 f"{before:,}", f"{before:,}", last)
        return
    rows = build_rows(c, lo, today)
    cfg = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition="WRITE_TRUNCATE" if last is None else "WRITE_APPEND",
    )
    c.load_table_from_json(rows, table, job_config=cfg).result()
    after = count_rows(c, table)
    log.info("ad_spend mode=append rows %s -> %s window=[%s, %s)",
             f"{before:,}", f"{after:,}", lo, today)


if __name__ == "__main__":
    main()