"""Streamlit dashboard over the gold layer. Launch with `uv run dental dashboard`."""

from __future__ import annotations

import json

import pandas as pd
import plotly.express as px
import streamlit as st

from dental_analytics.config import Settings
from dental_analytics.warehouse import GOLD_TABLES, WarehouseNotBuiltError, connect, read_gold

settings = Settings.from_env()

st.set_page_config(page_title="Denti-Cal Utilization", page_icon="🦷", layout="wide")


@st.cache_data(ttl=300)
def load_gold() -> dict[str, pd.DataFrame]:
    with connect(settings.duckdb_path) as con:
        return {table: read_gold(con, table) for table in GOLD_TABLES}


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


try:
    gold = load_gold()
except WarehouseNotBuiltError as exc:
    st.error(str(exc))
    st.stop()

kpis = gold["gold_program_kpis"].iloc[0]
segments = gold["gold_segment_summary"]
scorecard = gold["gold_provider_scorecard"]
quality = gold["gold_data_quality"]

st.title("Denti-Cal dental utilization")
st.caption(
    f"California Medi-Cal dental program, calendar year {int(kpis.calendar_year)} · "
    "bronze → silver → gold with dbt + DuckDB · every rate is a ratio of sums over published counts"
)

overview, segments_tab, providers_tab, quality_tab, brief_tab = st.tabs(
    ["Overview", "Segments", "Providers", "Data quality", "AI brief"]
)

with overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Providers", f"{kpis.providers:,}")
    c2.metric(
        "Provider-level patients",
        f"{kpis.provider_patients_observed / 1e6:.2f}M",
        help=(
            "Unique patients per provider, summed. A patient seen by two providers counts twice. "
            f"Including suppressed rows the true value is between {kpis.provider_patients_lower_bound:,} "
            f"and {kpis.provider_patients_upper_bound:,}."
        ),
    )
    c3.metric("Services per patient", f"{kpis.services_per_patient:.2f}")
    c4.metric("Preventive coverage", pct(kpis.preventive_coverage))

    by_age = segments[(segments.delivery_system == "ALL") & (segments.age_group != "ALL")]
    long = by_age.melt(
        id_vars="age_group",
        value_vars=["preventive_coverage", "exam_coverage", "treatment_coverage"],
        var_name="service",
        value_name="coverage",
    )
    long["service"] = long.service.str.replace("_coverage", "").str.title()
    fig = px.bar(
        long,
        x="service",
        y="coverage",
        color="age_group",
        barmode="group",
        text_auto=".1%",
        labels={"coverage": "Share of patients", "service": "", "age_group": "Age group"},
        title="Who receives which kind of care",
    )
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

with segments_tab:
    detail = segments[(segments.delivery_system != "ALL") & (segments.age_group != "ALL")]
    left, right = st.columns(2)
    with left:
        fig = px.bar(
            detail,
            x="delivery_system_name",
            y="preventive_coverage",
            color="age_group",
            barmode="group",
            text_auto=".1%",
            labels={"preventive_coverage": "Preventive coverage", "delivery_system_name": ""},
            title="Preventive coverage by delivery system",
        )
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.bar(
            detail,
            x="delivery_system_name",
            y="services_per_patient",
            color="age_group",
            barmode="group",
            text_auto=".2f",
            labels={"services_per_patient": "Services per patient", "delivery_system_name": ""},
            title="Service intensity by delivery system",
        )
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        segments.drop(columns=["delivery_system"]),
        hide_index=True,
        column_config={
            c: st.column_config.NumberColumn(format="percent")
            for c in ["suppressed_row_share", "preventive_coverage", "treatment_coverage", "exam_coverage"]
        },
    )

with providers_tab:
    age = st.radio("Age group", sorted(scorecard.age_group.unique()), horizontal=True)
    group = scorecard[scorecard.age_group == age]
    st.markdown(
        "Small practices produce extreme raw rates by chance. Each provider's preventive coverage is "
        "shrunk toward the age-group mean in proportion to how few patients back it "
        f"(empirical-Bayes beta-binomial; prior mean {pct(group.age_group_prior_mean.iloc[0])}, "
        f"prior strength ≈ {group.age_group_prior_strength.iloc[0]:.0f} patients)."
    )
    fig = px.scatter(
        group,
        x="coverage_patients",
        y=["raw_preventive_coverage", "shrunk_preventive_coverage"],
        log_x=True,
        opacity=0.45,
        hover_data=["provider_name", "rendering_npi"],
        labels={"coverage_patients": "Patients (log scale)", "value": "Preventive coverage", "variable": ""},
        title="Raw vs shrunk preventive coverage",
    )
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Highest preventive coverage (shrunk)")
    st.dataframe(
        group.nsmallest(15, "preventive_rank")[
            ["preventive_rank", "provider_name", "rendering_npi", "coverage_patients",
             "raw_preventive_coverage", "shrunk_preventive_coverage"]
        ],
        hide_index=True,
        column_config={
            "raw_preventive_coverage": st.column_config.NumberColumn(format="percent"),
            "shrunk_preventive_coverage": st.column_config.NumberColumn(format="percent"),
        },
    )
    st.subheader(f"Service-intensity outliers ({int(group.is_intensity_outlier.sum())} flagged)")
    st.caption("Modified z-score of services per patient above 3.5 (median/MAD). A screen for review, not a finding of wrongdoing.")
    st.dataframe(
        group[group.is_intensity_outlier]
        .sort_values("services_per_patient_robust_z", ascending=False)[
            ["provider_name", "rendering_npi", "patients_observed", "services_per_patient", "services_per_patient_robust_z"]
        ],
        hide_index=True,
    )

with quality_tab:
    q = quality.iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Source rows", f"{q.bronze_rows:,}")
    c2.metric("Duplicate rows removed", f"{q.duplicate_rows_removed:,}", help="Same provider, segment and metrics; only the name spelling differed.")
    c3.metric("Rows with suppressed patient count", pct(kpis.suppressed_row_share))
    fig = px.bar(
        quality,
        x="suppressed_share",
        y="measure",
        color="count_type",
        barmode="group",
        orientation="h",
        text_auto=".1%",
        labels={"suppressed_share": "Share of rows suppressed", "measure": "", "count_type": ""},
        title="Suppressed values by measure",
    )
    fig.update_xaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        "Counts between 1 and 10 are withheld at the source to protect privacy (annotation code 1), and "
        "some larger counts are withheld so the small ones cannot be derived (code 2). Silver keeps them "
        "as NULL instead of 0, and dbt tests enforce that a blank value always carries an annotation code."
    )

with brief_tab:
    brief_path = settings.reports_dir / "latest_brief.json"
    md_path = settings.reports_dir / "latest_brief.md"
    if md_path.exists():
        st.markdown(md_path.read_text())
        payload = json.loads(brief_path.read_text())
        with st.expander("Raw model output and fact-check details"):
            st.json(payload)
    else:
        st.info("No brief yet. Generate one with `uv run dental brief` (or `--offline`).")
