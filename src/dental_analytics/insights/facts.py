"""Turns gold tables into a flat, citable fact sheet.

The LLM never sees raw rows, only these facts. Every fact has a stable id so a
generated statement can cite exactly which numbers it relies on, and the
guardrails can check them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import duckdb

from dental_analytics.warehouse import read_gold

Unit = Literal["count", "share", "rate", "year"]


@dataclass(frozen=True)
class Fact:
    id: str
    label: str
    value: float
    unit: Unit

    @property
    def display(self) -> str:
        """The canonical rendering the LLM is asked to reuse verbatim."""
        if self.unit == "share":
            return f"{self.value * 100:.1f}%"
        if self.unit == "rate":
            return f"{self.value:.2f}"
        if self.unit == "year":
            return f"{self.value:.0f}"
        return f"{self.value:,.0f}"


def _add(facts: list[Fact], fact_id: str, label: str, value: object, unit: Unit) -> None:
    if value is None:
        return
    number = float(value)
    if math.isnan(number):
        return
    facts.append(Fact(fact_id, label, number, unit))


def _slug(value: str) -> str:
    return value.lower().replace("+", "plus").replace("-", "_")


def build_facts(con: duckdb.DuckDBPyConnection) -> list[Fact]:
    facts: list[Fact] = []

    kpis = read_gold(con, "gold_program_kpis").iloc[0]
    _add(facts, "program.calendar_year", "Calendar year of the data", kpis.calendar_year, "year")
    _add(facts, "program.providers", "Distinct rendering providers", kpis.providers, "count")
    _add(
        facts,
        "program.provider_patients_observed",
        "Provider-level patient count (published rows only; a patient seen by two providers counts twice)",
        kpis.provider_patients_observed,
        "count",
    )
    _add(
        facts,
        "program.provider_patients_upper_bound",
        "Provider-level patient count upper bound including suppressed rows",
        kpis.provider_patients_upper_bound,
        "count",
    )
    _add(facts, "program.services_observed", "Dental services (published rows)", kpis.services_observed, "count")
    _add(facts, "program.services_per_patient", "Services per patient", kpis.services_per_patient, "rate")
    for kind in ("preventive", "treatment", "exam"):
        _add(
            facts,
            f"program.{kind}_coverage",
            f"Share of patients who received at least one {kind} service",
            kpis[f"{kind}_coverage"],
            "share",
        )
    _add(
        facts,
        "quality.suppressed_row_share",
        "Share of provider rows whose patient count is suppressed for privacy",
        kpis.suppressed_row_share,
        "share",
    )

    quality = read_gold(con, "gold_data_quality").iloc[0]
    _add(
        facts,
        "quality.duplicate_rows_removed",
        "Source rows dropped as duplicates (same metrics, different name spelling)",
        quality.duplicate_rows_removed,
        "count",
    )

    segments = read_gold(con, "gold_segment_summary")
    for row in segments.itertuples(index=False):
        if row.delivery_system == "ALL" and row.age_group == "ALL":
            continue
        scope = f"{_slug(row.delivery_system)}.{_slug(row.age_group)}"
        who = (
            f"{row.delivery_system_name if row.delivery_system != 'ALL' else 'all delivery systems'}, "
            f"{'all ages' if row.age_group == 'ALL' else 'ages ' + row.age_group}"
        )
        _add(facts, f"segment.{scope}.providers", f"Providers ({who})", row.providers, "count")
        _add(
            facts,
            f"segment.{scope}.provider_patients_observed",
            f"Provider-level patient count ({who})",
            row.provider_patients_observed,
            "count",
        )
        _add(facts, f"segment.{scope}.services_per_patient", f"Services per patient ({who})", row.services_per_patient, "rate")
        for kind in ("preventive", "treatment", "exam"):
            _add(
                facts,
                f"segment.{scope}.{kind}_coverage",
                f"Share of patients with a {kind} service ({who})",
                getattr(row, f"{kind}_coverage"),
                "share",
            )

    scorecard = read_gold(con, "gold_provider_scorecard")
    for age_group, group in scorecard.groupby("age_group"):
        scope = _slug(str(age_group))
        _add(
            facts,
            f"providers.{scope}.intensity_outliers",
            f"Providers flagged as services-per-patient outliers (robust z > 3.5, ages {age_group})",
            int(group.is_intensity_outlier.sum()),
            "count",
        )
        _add(
            facts,
            f"providers.{scope}.median_services_per_patient",
            f"Median services per patient across providers (ages {age_group})",
            group.services_per_patient.median(),
            "rate",
        )
        top_decile = group.shrunk_preventive_coverage.quantile(0.9)
        bottom_decile = group.shrunk_preventive_coverage.quantile(0.1)
        _add(
            facts,
            f"providers.{scope}.preventive_coverage_p90",
            f"90th percentile of provider preventive coverage after shrinkage (ages {age_group})",
            top_decile,
            "share",
        )
        _add(
            facts,
            f"providers.{scope}.preventive_coverage_p10",
            f"10th percentile of provider preventive coverage after shrinkage (ages {age_group})",
            bottom_decile,
            "share",
        )

    return facts
