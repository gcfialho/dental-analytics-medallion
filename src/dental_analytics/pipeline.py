"""Builds and tests every dbt model (bronze -> silver -> gold) in one `dbt build`."""

from __future__ import annotations

import logging
import os

from dbt.cli.main import dbtRunner

from dental_analytics.config import Settings

log = logging.getLogger(__name__)


def run_dbt(settings: Settings, command: str = "build", extra_args: list[str] | None = None) -> bool:
    settings.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DUCKDB_PATH"] = str(settings.duckdb_path)
    # dbt resolves the CSV path relative to the working directory.
    os.chdir(settings.project_root)

    args = [
        command,
        "--project-dir", str(settings.dbt_project_dir),
        "--profiles-dir", str(settings.dbt_project_dir),
        *(extra_args or []),
    ]
    log.info("Running dbt %s", " ".join(args))
    result = dbtRunner().invoke(args)
    if result.exception:
        log.error("dbt crashed: %s", result.exception)
    return result.success
