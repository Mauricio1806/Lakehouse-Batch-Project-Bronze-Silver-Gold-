.PHONY: up down logs restart \
        ingest ge-check dbt-run dbt-test dbt-all \
        pipeline clean-data help

# ── Docker ──────────────────────────────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

restart:
	docker compose restart

# ── Local pipeline steps (run outside Docker, requires local Python env) ───
ingest:
	python -m src.ingest.tlc_download
	python -m src.ingest.tlc_to_bronze

ge-check:
	python -m src.ge.ge_run

dbt-run:
	cd dbt/lakehouse_dbt && \
	  DBT_PROFILES_DIR=. dbt run --profiles-dir . --project-dir .

dbt-test:
	cd dbt/lakehouse_dbt && \
	  DBT_PROFILES_DIR=. dbt test --profiles-dir . --project-dir .

dbt-all: dbt-run dbt-test

# ── Full end-to-end pipeline (local) ────────────────────────────────────────
pipeline: ingest ge-check dbt-all
	@echo "Pipeline complete. DuckDB: data/lakehouse.duckdb"

# ── Housekeeping ─────────────────────────────────────────────────────────────
clean-data:
	find data/raw     -name "*.parquet" -delete
	find data/bronze  -name "*.parquet" -delete
	find data/silver  -name "*.parquet" -delete
	find data/gold    -name "*.parquet" -delete

help:
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Docker:"
	@echo "  up            Start Airflow + Postgres in Docker"
	@echo "  down          Stop and remove containers + volumes"
	@echo "  logs          Tail all container logs"
	@echo "  restart       Restart all containers"
	@echo ""
	@echo "Local pipeline:"
	@echo "  ingest        Download TLC parquet + write Bronze"
	@echo "  ge-check      Great Expectations quality gate on Bronze"
	@echo "  dbt-run       Run dbt Silver + Gold models"
	@echo "  dbt-test      Run dbt schema tests"
	@echo "  pipeline      Full end-to-end (ingest → ge → dbt)"
	@echo ""
	@echo "Housekeeping:"
	@echo "  clean-data    Remove all generated parquet files"
	@echo ""
