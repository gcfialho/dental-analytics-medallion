"""Integration tests over the real dataset. They pin the corrections made in v2."""

import csv
from pathlib import Path

import pytest

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "denti_cal_2018.csv"


@pytest.fixture(scope="module")
def raw_rows() -> list[dict[str, str]]:
    with RAW.open() as f:
        return list(csv.DictReader(f, delimiter=";"))


def scalar(con, sql: str):
    return con.execute(sql).fetchone()[0]


def test_bronze_keeps_every_source_row(con, raw_rows):
    assert scalar(con, "select count(*) from bronze.bronze_denti_cal_utilization") == len(raw_rows)


def test_silver_drops_only_name_spelling_duplicates(con):
    assert scalar(con, "select duplicate_rows_removed from gold.gold_data_quality limit 1") == 501


def test_total_services_is_adv_not_a_sum_of_categories(con):
    """v1 added ADV + PREV + TXMT + EXAM, double counting (PREV/TXMT/EXAM are subsets of ADV)."""
    kpis = con.execute("select services_observed, services_per_patient from gold.gold_program_kpis").fetchone()
    silver_adv = scalar(con, "select sum(adv_services) from silver.silver_provider_utilization")
    assert kpis[0] == silver_adv
    assert 5 < kpis[1] < 8  # v1 reported 10.41


def test_suppressed_counts_are_null_not_zero(con):
    zeros = scalar(con, "select count(*) from silver.silver_provider_utilization where adv_users = 0")
    suppressed = scalar(con, "select count(*) from silver.silver_provider_utilization where adv_users_suppressed")
    assert zeros == 0
    assert suppressed > 5000


def test_patient_bounds_bracket_the_observed_total(con):
    lo, obs, hi = con.execute(
        "select provider_patients_lower_bound, provider_patients_observed, provider_patients_upper_bound "
        "from gold.gold_program_kpis"
    ).fetchone()
    assert obs < lo < hi


def test_segment_totals_match_program_kpis(con):
    program = con.execute("select services_per_patient, preventive_coverage from gold.gold_program_kpis").fetchone()
    overall = con.execute(
        "select services_per_patient, preventive_coverage from gold.gold_segment_summary "
        "where delivery_system = 'ALL' and age_group = 'ALL'"
    ).fetchone()
    assert overall == pytest.approx(program)


def test_children_have_higher_preventive_coverage_than_adults(con):
    rows = dict(
        con.execute(
            "select age_group, preventive_coverage from gold.gold_segment_summary "
            "where delivery_system = 'ALL' and age_group <> 'ALL'"
        ).fetchall()
    )
    assert rows["0-20"] > rows["21+"]


def test_shrinkage_pulls_small_practices_harder(con):
    small, large = con.execute(
        """
        select
            avg(abs(shrunk_preventive_coverage - raw_preventive_coverage)) filter (where coverage_patients < 30),
            avg(abs(shrunk_preventive_coverage - raw_preventive_coverage)) filter (where coverage_patients >= 500)
        from gold.gold_provider_scorecard
        """
    ).fetchone()
    assert small > large
