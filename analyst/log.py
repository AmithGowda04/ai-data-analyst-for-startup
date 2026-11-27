"""Append one row per question to ops.query_log (written with the loader key)."""
import datetime
import os

from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account

load_dotenv(override=True)

SCHEMA = [
    bigquery.SchemaField("ts", "TIMESTAMP"),
    bigquery.SchemaField("run_id", "STRING"),
    bigquery.SchemaField("question", "STRING"),
    bigquery.SchemaField("sql_text", "STRING"),
    bigquery.SchemaField("status", "STRING"),
    bigquery.SchemaField("message", "STRING"),
    bigquery.SchemaField("model", "STRING"),
    bigquery.SchemaField("bytes_estimated", "INT64"),
    bigquery.SchemaField("bytes_billed", "INT64"),
    bigquery.SchemaField("seconds", "FLOAT64"),
    bigquery.SchemaField("row_count", "INT64"),
]
_client = None


def _loader():
    global _client
    if _client is None:
        project = os.environ["GCP_PROJECT_ID"]
        creds = service_account.Credentials.from_service_account_file(os.environ["LOADER_KEY_PATH"])
        _client = bigquery.Client(project=project, credentials=creds, location="US")
        ds = bigquery.Dataset(f"{project}.ops")
        ds.location = "US"
        _client.create_dataset(ds, exists_ok=True)
    return _client


def log_query(res, run_id="manual"):
    """Never raises: a logging failure must not break an answer."""
    try:
        row = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "run_id": run_id,
            "question": res["question"],
            "sql_text": res.get("sql"),
            "status": res["status"],
            "message": res.get("message", ""),
            "model": res.get("model"),
            "bytes_estimated": int(res.get("bytes_estimated", 0)),
            "bytes_billed": int(res.get("bytes_billed", 0)),
            "seconds": res.get("seconds"),
            "row_count": len(res.get("rows", [])),
        }
        table = f"{os.environ['GCP_PROJECT_ID']}.ops.query_log"
        cfg = bigquery.LoadJobConfig(schema=SCHEMA, write_disposition="WRITE_APPEND")
        _loader().load_table_from_json([row], table, job_config=cfg).result()
    except Exception as e:
        print(f"[query_log] not written: {str(e)[:150]}")