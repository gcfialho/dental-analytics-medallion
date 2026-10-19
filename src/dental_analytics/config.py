"""Runtime settings, resolved from environment variables with repo-relative defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _project_root() -> Path:
    if root := os.getenv("DENTAL_PROJECT_ROOT"):
        return Path(root).resolve()
    # src/dental_analytics/config.py -> repository root
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    project_root: Path
    duckdb_path: Path
    dbt_project_dir: Path
    reports_dir: Path
    openai_model: str

    @classmethod
    def from_env(cls) -> Settings:
        root = _project_root()
        duckdb_path = Path(os.getenv("DUCKDB_PATH", root / "warehouse" / "dental.duckdb"))
        if not duckdb_path.is_absolute():
            duckdb_path = root / duckdb_path
        return cls(
            project_root=root,
            duckdb_path=duckdb_path,
            dbt_project_dir=root / "transform",
            reports_dir=Path(os.getenv("REPORTS_DIR", root / "reports")),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        )
