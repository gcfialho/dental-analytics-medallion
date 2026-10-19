from types import SimpleNamespace

from dental_analytics.insights import llm
from dental_analytics.insights.facts import build_facts
from dental_analytics.insights.guardrails import verify_brief
from dental_analytics.insights.offline import build_offline_brief
from dental_analytics.insights.schema import Finding, InsightsBrief


def test_fact_ids_are_unique(con):
    ids = [fact.id for fact in build_facts(con)]
    assert len(ids) == len(set(ids))


def test_offline_brief_passes_its_own_fact_check(con):
    facts = build_facts(con)
    verified = verify_brief(build_offline_brief(facts), facts)
    assert verified.rejected == []
    assert verified.headline_issue is None
    assert len(verified.accepted) == 5


class FakeResponses:
    def __init__(self, parsed: InsightsBrief):
        self.parsed = parsed
        self.calls: list[dict] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_parsed=self.parsed)


def test_llm_path_sends_facts_and_returns_structured_brief(con):
    facts = build_facts(con)
    fake_brief = InsightsBrief(
        headline="Fake",
        findings=[Finding(kind="observation", title="x", statement="Made up 99.9%.", metric_ids=[facts[0].id])],
        caveats=[],
    )
    responses = FakeResponses(fake_brief)
    client = SimpleNamespace(responses=responses)

    brief = llm.generate_brief(facts, model="test-model", client=client)

    assert brief == fake_brief
    call = responses.calls[0]
    assert call["model"] == "test-model"
    assert call["text_format"] is InsightsBrief
    assert facts[0].id in str(call["input"])
    # The hallucinated number is caught downstream.
    assert verify_brief(brief, facts).accepted == []
