# AI Data Analyst for a Startup

**For whom:** a startup founder who asks "why did revenue dip last week?" and needs a correct, sourced answer.

An Airflow-orchestrated BigQuery warehouse combining sales, ad spend and product events. A dbt metrics layer defines revenue, AOV, CAC, ROAS, conversion and retention once, and an LLM turns plain-English questions into SQL against that governed layer only (never raw tables), with SQL validation and cost guards.


## Architecture
Sources (thelook_ecommerce, GA4 sample, generated ad spend) -> Airflow DAGs (incremental loads) -> BigQuery raw -> dbt (staging -> marts -> metrics) -> LLM text-to-SQL (metric context, sqlglot validation, dry-run cost guard) -> Streamlit chat (answer + SQL + chart).



