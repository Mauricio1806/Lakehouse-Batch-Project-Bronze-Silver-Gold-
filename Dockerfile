FROM apache/airflow:2.9.3

USER airflow
RUN pip install --no-cache-dir \
    duckdb==1.1.3 \
    dbt-duckdb==1.8.3 \
    pandas==2.2.3 \
    plotly==5.24.1 \
    requests==2.32.3 \
    pyyaml==6.0.2
