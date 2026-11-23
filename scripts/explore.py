import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()
client = bigquery.Client(project=os.environ["GCP_PROJECT_ID"])
DS = "bigquery-public-data.thelook_ecommerce"

for t in ["orders", "order_items", "users", "products", "events"]:
    cols = client.query(
        f"SELECT column_name, data_type FROM `{DS}.INFORMATION_SCHEMA.COLUMNS` "
        f"WHERE table_name = '{t}' ORDER BY ordinal_position"
    ).result()
    n = list(client.query(f"SELECT COUNT(*) AS n FROM `{DS}.{t}`").result())[0].n
    print(f"\n== {t} ({n:,} rows)")
    for c in cols:
        print(f"  {c.column_name}: {c.data_type}")