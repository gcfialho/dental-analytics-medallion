.PHONY: setup pipeline brief dashboard docs test lint format all

setup:      ## Install dependencies
	uv sync

pipeline:   ## Build + test bronze, silver and gold
	uv run dental pipeline

brief:      ## Fact-checked insights brief (LLM if OPENAI_API_KEY is set)
	uv run dental brief

dashboard:  ## Streamlit dashboard on http://localhost:8501
	uv run dental dashboard

docs:       ## dbt docs with lineage graph on http://localhost:8080
	DUCKDB_PATH=warehouse/dental.duckdb uv run dbt docs generate --project-dir transform --profiles-dir transform
	DUCKDB_PATH=warehouse/dental.duckdb uv run dbt docs serve --project-dir transform --profiles-dir transform

test:       ## Python tests (includes a full dbt build in a temp warehouse)
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

all: setup pipeline brief dashboard
