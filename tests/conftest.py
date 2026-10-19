import os
from pathlib import Path

import pytest

from dental_analytics.config import Settings
from dental_analytics.pipeline import run_dbt
from dental_analytics.warehouse import connect


@pytest.fixture(scope="session")
def settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    tmp = tmp_path_factory.mktemp("warehouse")
    os.environ["DUCKDB_PATH"] = str(tmp / "dental.duckdb")
    os.environ["REPORTS_DIR"] = str(tmp / "reports")
    return Settings.from_env()


@pytest.fixture(scope="session")
def built_warehouse(settings: Settings) -> Path:
    """Runs the real `dbt build` (models + all data tests) once per test session."""
    cwd = Path.cwd()
    try:
        assert run_dbt(settings, "build"), "dbt build failed; see the dbt log above"
    finally:
        os.chdir(cwd)
    return settings.duckdb_path


@pytest.fixture
def con(built_warehouse: Path):
    with connect(built_warehouse) as connection:
        yield connection
