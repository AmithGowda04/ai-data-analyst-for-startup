import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()
client = bigquery.Client(project=os.environ["GCP_PROJECT_ID"])
sql = """
SELECT MIN(created_at) AS first_order, MAX(created_at) AS last_order, COUNT(*) AS n
FROM `bigquery-public-data.thelook_ecommerce.orders`
"""
for row in client.query(sql).result():
    print(dict(row))