.PHONY: up down logs restart \
        ingest ge-check \
        dbt-silver dbt-gold dbt-all dbt-test \
        profile report \
        pipeline clean-data help

# ── Docker ───────────────────────────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

restart:
	docker compose restart

# ── Local pipeline steps ─────────────────────────────────────────────────
ingest:
	python -m src.ingest.tlc_download
	python -m src.ingest.tlc_to_bronze

ge-check:
	python -m src.ge.ge_run

dbt-silver:
	cd dbt/lakehouse_dbt && dbt run --select stg_trips --profiles-dir .

dbt-gold:
	cd dbt/lakehouse_dbt && dbt run --select gold --profiles-dir .

dbt-all: dbt-silver dbt-gold

dbt-test:
	cd dbt/lakehouse_dbt && dbt test --profiles-dir .

profile:
	python -m src.analytics.profile

report:
	python -m src.analytics.report
	@echo "Report saved to reports/"

# ── Full end-to-end pipeline ─────────────────────────────────────────────
pipeline: ingest ge-check dbt-all dbt-test profile report
	@echo ""
	@echo "Pipeline complete."
	@echo "DuckDB  : data/lakehouse.duckdb"
	@echo "Report  : reports/"

# ── Housekeeping ─────────────────────────────────────────────────────────
clean-data:
	find data/raw    -name "*.parquet" -delete 2>/dev/null || true
	find data/bronze -name "*.parquet" -delete 2>/dev/null || true
	find data/silver -name "*.parquet" -delete 2>/dev/null || true
	find data/gold   -name "*.parquet" -delete 2>/dev/null || true
	rm -f data/lakehouse.duckdb

help:
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "  Docker:"
	@echo "    up            Start Airflow + Postgres in Docker"
	@echo "    down          Stop and remove containers + volumes"
	@echo "    logs          Tail all container logs"
	@echo "    restart       Restart containers"
	@echo ""
	@echo "  Local pipeline:"
	@echo "    ingest        Download TLC parquet + write Bronze"
	@echo "    ge-check      Quality gate on Bronze"
	@echo "    dbt-silver    Run stg_trips model"
	@echo "    dbt-gold      Run all Gold models"
	@echo "    dbt-test      Run dbt schema tests"
	@echo "    profile       Data profiler (prints + saves txt)"
	@echo "    report        Generate HTML analytics dashboard"
	@echo "    pipeline      Full end-to-end run"
	@echo ""
	@echo "  Housekeeping:"
	@echo "    clean-data    Remove all generated parquet + duckdb files"
	@echo ""
