from __future__ import annotations

from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator

DEFAULT_ENV = {
    "PYTHONUNBUFFERED": "1",
}

with DAG(
    dag_id="lakehouse_bronze_silver_gold",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["lakehouse", "duckdb", "dbt", "great_expectations"],
) as dag:

    ingest_bronze = BashOperator(
        task_id="01_ingest_bronze",
        bash_command="python -m src.ingest.tlc_download && python -m src.ingest.tlc_to_bronze",
        env=DEFAULT_ENV,
    )

    ge_gate = BashOperator(
        task_id="02_ge_quality_gate",
        bash_command="python -m src.ge.ge_run",
        env=DEFAULT_ENV,
    )

    dbt_silver = BashOperator(
        task_id="03_dbt_silver",
        bash_command="cd dbt/lakehouse_dbt && dbt run --select models/silver",
        env=DEFAULT_ENV,
    )

    dbt_gold = BashOperator(
        task_id="04_dbt_gold",
        bash_command="cd dbt/lakehouse_dbt && dbt run --select models/gold",
        env=DEFAULT_ENV,
    )

    ingest_bronze >> ge_gate >> dbt_silver >> dbt_gold
