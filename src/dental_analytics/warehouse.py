"""Read-only access to the gold layer of the DuckDB warehouse."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

GOLD_TABLES = (
    "gold_program_kpis",
    "gold_segment_summary",
    "gold_provider_scorecard",
    "gold_data_quality",
)


class WarehouseNotBuiltError(FileNotFoundError):
    """Raised when the DuckDB file does not exist yet (run the pipeline first)."""


def connect(path: Path) -> duckdb.DuckDBPyConnection:
    if not path.exists():
        raise WarehouseNotBuiltError(f"No warehouse at {path}. Build it with `uv run dental pipeline`.")
    return duckdb.connect(str(path), read_only=True)


def read_gold(con: duckdb.DuckDBPyConnection, table: str) -> pd.DataFrame:
    if table not in GOLD_TABLES:
        raise ValueError(f"Unknown gold table: {table}")
    return con.execute(f"select * from gold.{table}").df()
