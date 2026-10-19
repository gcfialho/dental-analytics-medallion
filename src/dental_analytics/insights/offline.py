"""Deterministic brief used when no LLM is configured (and as a CI baseline).

It goes through the same schema and guardrails as the LLM path, so the
dashboard and tests exercise one code path regardless of the backend.
"""

from __future__ import annotations

from dental_analytics.insights.facts import Fact
from dental_analytics.insights.schema import Finding, InsightsBrief


def build_offline_brief(facts: list[Fact]) -> InsightsBrief:
    f = {fact.id: fact for fact in facts}

    def d(fact_id: str) -> str:
        return f[fact_id].display

    findings = [
        Finding(
            kind="observation",
            title="Children get far more preventive care than adults",
            statement=(
                f"{d('segment.all.0_20.preventive_coverage')} of patients aged 0-20 received a preventive "
                f"service, versus {d('segment.all.21plus.preventive_coverage')} of adults."
            ),
            metric_ids=["segment.all.0_20.preventive_coverage", "segment.all.21plus.preventive_coverage"],
        ),
        Finding(
            kind="observation",
            title="Adults lean on treatment rather than prevention",
            statement=(
                f"{d('segment.all.21plus.treatment_coverage')} of adult patients received a treatment "
                f"service, compared with {d('segment.all.0_20.treatment_coverage')} of children."
            ),
            metric_ids=["segment.all.21plus.treatment_coverage", "segment.all.0_20.treatment_coverage"],
        ),
        Finding(
            kind="observation",
            title="Fee-for-Service dominates the program",
            statement=(
                f"Fee-for-Service accounts for {d('segment.ffs.all.provider_patients_observed')} of "
                f"{d('program.provider_patients_observed')} provider-level patient counts."
            ),
            metric_ids=["segment.ffs.all.provider_patients_observed", "program.provider_patients_observed"],
        ),
        Finding(
            kind="observation",
            title="Wide spread in preventive coverage between providers",
            statement=(
                f"After shrinkage, the provider at the 90th percentile reaches "
                f"{d('providers.0_20.preventive_coverage_p90')} preventive coverage for children, "
                f"against {d('providers.0_20.preventive_coverage_p10')} at the 10th percentile."
            ),
            metric_ids=["providers.0_20.preventive_coverage_p90", "providers.0_20.preventive_coverage_p10"],
        ),
        Finding(
            kind="recommendation",
            title="Review providers with unusual service intensity",
            statement=(
                f"{d('providers.21plus.intensity_outliers')} adult-care and "
                f"{d('providers.0_20.intensity_outliers')} child-care provider profiles bill an unusual number "
                "of services per patient and are worth a claims review."
            ),
            metric_ids=["providers.21plus.intensity_outliers", "providers.0_20.intensity_outliers"],
        ),
    ]

    return InsightsBrief(
        headline=(
            f"{d('program.providers')} providers delivered {d('program.services_per_patient')} services "
            f"per patient in {d('program.calendar_year')}, with {d('program.preventive_coverage')} of "
            "patients receiving preventive care."
        ),
        findings=findings,
        caveats=[
            "Patient counts are unique per provider, so totals count a patient once per provider seen.",
            "Counts under the small-cell threshold are suppressed at the source and excluded from rates.",
            "Coverage is a utilization measure, not a measure of clinical quality or outcomes.",
        ],
    )
