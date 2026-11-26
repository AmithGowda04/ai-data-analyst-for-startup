# 0003: Airflow orchestration and duplicate prevention

## Context
- Loads must run daily, be safe to re-run, and show failures clearly.
- Dev machine is a Codespace (7.8 GB RAM, 2 cores): the official Celery compose setup is too heavy.
- BigQuery sandbox has no DML, so we cannot DELETE-then-INSERT or MERGE.

## Decision
- Airflow 3.4 in Docker with LocalExecutor (api-server, dag-processor, scheduler, Postgres, Redis).
  Celery worker and triggerer are in a compose profile that is not started.
- One DAG, `ingest_raw`, with three sequential tasks: load raw tables -> load ad spend -> record row counts.
- Schedule: 02:00 UTC daily, `catchup=False`, `max_active_runs=1`, 2 retries with a 2-minute delay,
  failure callback writes an error log line.
- Incremental by date, where it matters:
  - events and ad_spend append only complete days after the destination's max date (UTC, up to yesterday).
  - small mutable tables (orders, order_items, users, products) are replaced each run.
- Duplicates are prevented by construction:
  1. The watermark is read from the destination table, not from Airflow state.
  2. Only complete days are loaded, so a day is never loaded twice.
  3. Each load is one atomic BigQuery job, so a failure leaves no partial rows.
  4. `max_active_runs=1` stops two runs appending the same window at once.
- Secrets: the loader key is mounted read-only from outside the image; it is never baked into an image or committed.

## Evidence
- Two consecutive DAG runs gave identical row counts per table (see raw.load_log).
- DAG run duration: [first run] s, [second run] s (measured in a Codespace).

## Consequences
- Airflow state can be lost without losing correctness, because the watermark lives in the data.
- A source day that changes after it is loaded is not corrected for events (immutable by assumption).
- LocalExecutor runs tasks on the scheduler host: fine for one daily DAG, not for parallel workloads.
- Sandbox tables expire after 60 days; running the DAG rebuilds them.