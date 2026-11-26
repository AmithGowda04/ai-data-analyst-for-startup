"""Daily raw ingest: thelook -> raw.*, then ad spend, then a row-count log."""
import datetime
import logging

from airflow.sdk import dag, task

log = logging.getLogger(__name__)


def _on_failure(context):
    ti = context.get("task_instance") or context.get("ti")
    log.error("INGEST FAILED dag=%s task=%s run=%s",
              getattr(ti, "dag_id", "?"), getattr(ti, "task_id", "?"), context.get("run_id"))


@dag(
    dag_id="ingest_raw",
    schedule="0 2 * * *",  # 02:00 UTC daily: yesterday is complete by then
    start_date=datetime.datetime(2026, 11, 1, tzinfo=datetime.timezone.utc),
    catchup=False,
    max_active_runs=1,  # concurrent runs could append the same window twice
    default_args={
        "retries": 2,
        "retry_delay": datetime.timedelta(minutes=2),
        "on_failure_callback": _on_failure,
    },
    tags=["ingest"],
)
def ingest_raw():
    @task
    def load_raw_tables():
        import load_raw
        load_raw.main()

    @task
    def load_ad_spend_task():
        import load_ad_spend
        load_ad_spend.main()

    @task
    def record_counts_task():
        import run_all
        run_id, rows = run_all.record_counts()
        for r in rows:
            log.info("run=%s %s rows=%s", run_id, r["table_name"], r["row_count"])

    load_raw_tables() >> load_ad_spend_task() >> record_counts_task()


ingest_raw()