import os

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()
P = os.environ["GCP_PROJECT_ID"]
c = bigquery.Client(project=P)  # uses GOOGLE_APPLICATION_CREDENTIALS = the read-only key


def try_count(table):
    try:
        n = list(c.query(f"SELECT COUNT(*) AS n FROM `{P}.{table}`").result())[0].n
        return f"OK ({n:,} rows)"
    except Exception as e:
        return f"BLOCKED ({type(e).__name__})"


for t in ["marts.metrics_daily", "marts.fct_orders", "raw.orders", "raw.users", "staging.stg_orders"]:
    print(f"{t:<22} {try_count(t)}")