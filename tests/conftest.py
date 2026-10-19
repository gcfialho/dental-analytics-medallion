import os
import subprocess
import sys
from pathlib import Path

import pytest

from dental_analytics.config import Settings
from dental_analytics.warehouse import connect


@pytest.fixture(scope="session")
def settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    tmp = tmp_path_factory.mktemp("warehouse")
    os.environ["DUCKDB_PATH"] = str(tmp / "dental.duckdb")
    os.environ["REPORTS_DIR"] = str(tmp / "reports")
    return Settings.from_env()


@pytest.fixture(scope="session")
def built_warehouse(settings: Settings) -> Path:
    """Runs the real `dbt build` (models + all data tests) once per test session.

    It runs in a subprocess: dbt-duckdb keeps its read-write connection open for the
    life of the process, and DuckDB refuses a second, read-only connection to the
    same file from that process.
    """
    result = subprocess.run([sys.executable, "-m", "dental_analytics.cli", "pipeline"], env=os.environ.copy())
    assert result.returncode == 0, "dbt build failed; see the dbt log above"
    return settings.duckdb_path


@pytest.fixture
def con(built_warehouse: Path):
    with connect(built_warehouse) as connection:
        yield connection
