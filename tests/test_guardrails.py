from dental_analytics.insights.facts import Fact
from dental_analytics.insights.guardrails import extract_quantities, unsupported_quantities, verify_brief
from dental_analytics.insights.schema import Finding, InsightsBrief

FACTS = [
    Fact("kids.preventive", "Preventive coverage, ages 0-20", 0.6612, "share"),
    Fact("adults.preventive", "Preventive coverage, ages 21+", 0.2843, "share"),
    Fact("program.patients", "Provider-level patients", 6_842_769, "count"),
    Fact("program.spp", "Services per patient", 6.371, "rate"),
    Fact("program.year", "Calendar year", 2018, "year"),
]


def finding(statement: str, metric_ids: list[str]) -> Finding:
    return Finding(kind="observation", title="t", statement=statement, metric_ids=metric_ids)


def test_extracts_percent_scale_and_thousands_separators():
    quantities = extract_quantities("66.1% of 6,842,769 patients, about 6.8 million, 6.37 each")
    assert [(q.value, q.is_percent) for q in quantities] == [
        (66.1, True),
        (6_842_769, False),
        (6_800_000, False),
        (6.37, False),
    ]


def test_age_group_labels_are_not_quantities():
    assert extract_quantities("patients aged 0-20 and adults 21+") == []


def test_rounding_must_match_the_precision_written():
    assert unsupported_quantities("66.1%", FACTS) == []
    assert unsupported_quantities("66%", FACTS) == []
    # 66.4% is not a rounding of 66.12%.
    assert unsupported_quantities("66.4%", FACTS) == ["66.4%"]
    assert unsupported_quantities("about 6.8 million", FACTS) == []
    assert unsupported_quantities("about 7.1 million", FACTS) == ["7.1 million"]


def test_percent_never_matches_a_count_or_rate():
    assert unsupported_quantities("6.37%", FACTS) == ["6.37%"]


def test_accepts_finding_backed_by_cited_facts():
    brief = InsightsBrief(
        headline="In 2018, 6.37 services were delivered per patient.",
        findings=[
            finding(
                "66.1% of children vs 28.4% of adults got preventive care.", ["kids.preventive", "adults.preventive"]
            )
        ],
        caveats=[],
    )
    verified = verify_brief(brief, FACTS)
    assert verified.headline_issue is None
    assert len(verified.accepted) == 1
    assert verified.rejected == []


def test_rejects_hallucinated_number():
    brief = InsightsBrief(
        headline="ok",
        findings=[finding("Preventive coverage for children doubled to 71.0%.", ["kids.preventive"])],
        caveats=[],
    )
    verified = verify_brief(brief, FACTS)
    assert verified.accepted == []
    assert "71.0%" in verified.rejected[0][1]


def test_rejects_number_from_an_uncited_fact():
    # 28.4% is a real fact, but the finding only cites the children's metric.
    brief = InsightsBrief(
        headline="ok",
        findings=[finding("Adults reached 28.4%.", ["kids.preventive"])],
        caveats=[],
    )
    assert verify_brief(brief, FACTS).accepted == []


def test_rejects_unknown_or_missing_citations():
    brief = InsightsBrief(
        headline="ok",
        findings=[finding("No numbers here.", []), finding("No numbers here.", ["made.up"])],
        caveats=[],
    )
    reasons = [reason for _, reason in verify_brief(brief, FACTS).rejected]
    assert reasons == ["cites no facts", "cites unknown facts: made.up"]


def test_flags_unsupported_headline():
    brief = InsightsBrief(headline="Coverage hit 90%.", findings=[], caveats=[])
    verified = verify_brief(brief, FACTS)
    assert verified.headline is None
    assert "90%" in verified.headline_issue
