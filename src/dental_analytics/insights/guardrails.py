"""Fact-checks a generated brief against the fact sheet before anyone reads it.

A finding is accepted only if (1) it cites at least one known fact id and (2) every
number in its text matches the value of one of the facts it cites. The headline is
checked against the whole fact sheet. Rejected findings are kept with the reason so
failures stay visible instead of silently disappearing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from dental_analytics.insights.facts import Fact
from dental_analytics.insights.schema import Finding, InsightsBrief

# Labels that contain digits but are not quantities.
_NON_QUANTITIES = re.compile(
    r"\b0-20\b|\b21\+|\bages? \d+(?:-\d+)?\b|\bz\s*>\s*3\.5\b"
    r"|\b\d+(?:st|nd|rd|th)\b",  # ordinals ("90th percentile") are labels, not quantities
    re.IGNORECASE,
)
_NUMBER = re.compile(
    r"(?<![\w.])(?P<num>\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(?P<suffix>%|million|thousand|[MK]\b)?",
    re.IGNORECASE,
)
_SCALE = {"million": 1e6, "m": 1e6, "thousand": 1e3, "k": 1e3}


@dataclass(frozen=True)
class Quantity:
    text: str
    value: float
    is_percent: bool
    tolerance: float  # half a unit of the last digit written, after scaling


@dataclass
class VerifiedBrief:
    headline: str | None
    accepted: list[Finding] = field(default_factory=list)
    rejected: list[tuple[Finding, str]] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    headline_issue: str | None = None


def extract_quantities(text: str) -> list[Quantity]:
    cleaned = _NON_QUANTITIES.sub(" ", text)
    quantities = []
    for match in _NUMBER.finditer(cleaned):
        digits = match["num"].replace(",", "")
        decimals = len(digits.split(".")[1]) if "." in digits else 0
        suffix = (match["suffix"] or "").lower()
        scale = _SCALE.get(suffix, 1)
        quantities.append(
            Quantity(
                text=match.group(0).strip(),
                value=float(digits) * scale,
                is_percent=suffix == "%",
                tolerance=0.5 * 10**-decimals * scale + 1e-9,
            )
        )
    return quantities


def _matches(quantity: Quantity, fact: Fact) -> bool:
    """True if the written number is the fact's value rounded to the precision shown."""
    if quantity.is_percent != (fact.unit == "share"):
        return False
    target = fact.value * 100 if fact.unit == "share" else fact.value
    return abs(quantity.value - target) <= quantity.tolerance


def unsupported_quantities(text: str, facts: list[Fact]) -> list[str]:
    return [q.text for q in extract_quantities(text) if not any(_matches(q, f) for f in facts)]


def verify_brief(brief: InsightsBrief, facts: list[Fact]) -> VerifiedBrief:
    by_id = {fact.id: fact for fact in facts}
    verified = VerifiedBrief(headline=brief.headline, caveats=list(brief.caveats))

    if bad := unsupported_quantities(brief.headline, facts):
        verified.headline = None
        verified.headline_issue = f"unsupported numbers: {', '.join(bad)}"

    for finding in brief.findings:
        unknown = [m for m in finding.metric_ids if m not in by_id]
        if not finding.metric_ids:
            verified.rejected.append((finding, "cites no facts"))
            continue
        if unknown:
            verified.rejected.append((finding, f"cites unknown facts: {', '.join(unknown)}"))
            continue
        cited = [by_id[m] for m in finding.metric_ids]
        if bad := unsupported_quantities(f"{finding.title} {finding.statement}", cited):
            verified.rejected.append((finding, f"numbers not backed by cited facts: {', '.join(bad)}"))
            continue
        verified.accepted.append(finding)

    return verified
