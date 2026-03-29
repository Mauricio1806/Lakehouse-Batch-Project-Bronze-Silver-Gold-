from __future__ import annotations

from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator

WORKDIR = "/opt/airflow"

DEFAULT_ENV = {
    "PYTHONUNBUFFERED": "1",
    "PYTHONPATH":       WORKDIR,
    "LAKEHOUSE_ROOT":   WORKDIR,
    "LAKEHOUSE_DB_PATH": f"{WORKDIR}/data/lakehouse.duckdb",
    "PATH": "/home/airflow/.local/bin:/usr/local/bin:/usr/bin:/bin",
    "HOME": "/home/airflow",
}

with DAG(
    dag_id="lakehouse_bronze_silver_gold",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["lakehouse", "duckdb", "dbt", "great_expectations"],
) as dag:

    # ── 01  Ingest ──────────────────────────────────────────────────────
    ingest_bronze = BashOperator(
        task_id="01_ingest_bronze",
        bash_command=(
            "python -m src.ingest.tlc_download && "
            "python -m src.ingest.tlc_to_bronze"
        ),
        env=DEFAULT_ENV,
        cwd=WORKDIR,
    )

    # ── 02  Quality Gate ────────────────────────────────────────────────
    ge_gate = BashOperator(
        task_id="02_ge_quality_gate",
        bash_command="python -m src.ge.ge_run",
        env=DEFAULT_ENV,
        cwd=WORKDIR,
    )

    # ── 03  Silver model ────────────────────────────────────────────────
    dbt_silver = BashOperator(
        task_id="03_dbt_silver",
        bash_command=(
            f"cd {WORKDIR}/dbt/lakehouse_dbt && "
            "dbt run --select stg_trips --profiles-dir ."
        ),
        env=DEFAULT_ENV,
        cwd=WORKDIR,
    )

    # ── 04  All Gold models ─────────────────────────────────────────────
    dbt_gold = BashOperator(
        task_id="04_dbt_gold",
        bash_command=(
            f"cd {WORKDIR}/dbt/lakehouse_dbt && "
            "dbt run --select gold --profiles-dir ."
        ),
        env=DEFAULT_ENV,
        cwd=WORKDIR,
    )

    # ── 05  dbt tests (Silver + Gold) ───────────────────────────────────
    dbt_tests = BashOperator(
        task_id="05_dbt_tests",
        bash_command=(
            f"cd {WORKDIR}/dbt/lakehouse_dbt && "
            "dbt test --profiles-dir ."
        ),
        env=DEFAULT_ENV,
        cwd=WORKDIR,
    )

    # ── 06  Data profiler ───────────────────────────────────────────────
    profiler = BashOperator(
        task_id="06_data_profile",
        bash_command="python -m src.analytics.profile",
        env=DEFAULT_ENV,
        cwd=WORKDIR,
    )

    # ── 07  Analytics report ────────────────────────────────────────────
    analytics_report = BashOperator(
        task_id="07_analytics_report",
        bash_command="python -m src.analytics.report",
        env=DEFAULT_ENV,
        cwd=WORKDIR,
    )

    # ── 08  Grafana JSON export ─────────────────────────────────────────
    grafana_export = BashOperator(
        task_id="08_grafana_export",
        bash_command="python -m src.analytics.grafana_export",
        env=DEFAULT_ENV,
        cwd=WORKDIR,
    )

    # ── DAG wiring ──────────────────────────────────────────────────────
    ingest_bronze >> ge_gate >> dbt_silver >> dbt_gold >> dbt_tests >> profiler >> analytics_report >> grafana_export
