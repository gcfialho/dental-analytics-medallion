"""LLM brief generation with OpenAI structured outputs.

The model receives only the fact sheet (ids, labels, display values) and must
return an `InsightsBrief`. It is never trusted: `guardrails.verify_brief` checks
every number before the brief is shown.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from dental_analytics.insights.facts import Fact
from dental_analytics.insights.schema import InsightsBrief

if TYPE_CHECKING:
    from openai import OpenAI

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a healthcare data analyst writing a brief for program managers of
California's Medi-Cal dental program (Denti-Cal).

You are given a fact sheet. Each fact has an `id`, a `label` and a `display` value.

Rules:
- Use only the facts provided. Do not use outside knowledge about the program.
- Copy numbers exactly as written in `display`. Never compute new numbers (no
  differences, ratios or multiples).
- Every finding must list in `metric_ids` the id of every fact whose number it uses.
- Patient counts are per provider: never call them distinct beneficiaries.
- Coverage measures utilization, not clinical quality. Do not imply causation.
- Do not name individual providers.

Write 4 to 6 observations and 1 to 3 recommendations, plus caveats about the data.
"""


def _fact_sheet(facts: list[Fact]) -> str:
    rows = [{"id": f.id, "label": f.label, "display": f.display} for f in facts]
    return json.dumps(rows, indent=1)


def generate_brief(facts: list[Fact], model: str, client: OpenAI | None = None) -> InsightsBrief:
    if client is None:
        from openai import OpenAI

        client = OpenAI()

    response = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Fact sheet:\n{_fact_sheet(facts)}"},
        ],
        text_format=InsightsBrief,
    )
    brief = response.output_parsed
    if brief is None:
        raise RuntimeError("The model returned no parsable brief (possibly a refusal).")
    log.info("Model returned %d findings", len(brief.findings))
    return brief
