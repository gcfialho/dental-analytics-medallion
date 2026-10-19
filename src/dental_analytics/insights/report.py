"""Renders a verified brief to Markdown and persists it next to its raw JSON."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from dental_analytics.insights.guardrails import VerifiedBrief
from dental_analytics.insights.schema import InsightsBrief


@dataclass(frozen=True)
class BriefMetadata:
    backend: str  # "openai:<model>" or "offline"
    generated_at: str

    @classmethod
    def now(cls, backend: str) -> BriefMetadata:
        return cls(backend=backend, generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"))


def render_markdown(verified: VerifiedBrief, meta: BriefMetadata) -> str:
    lines = ["# Denti-Cal utilization brief", ""]
    lines.append(f"_Generated {meta.generated_at} by `{meta.backend}`. Every number below was checked against the gold layer._")
    lines.append("")
    if verified.headline:
        lines += [f"**{verified.headline}**", ""]

    for kind, heading in (("observation", "Findings"), ("recommendation", "Recommendations")):
        items = [f for f in verified.accepted if f.kind == kind]
        if items:
            lines += [f"## {heading}", ""]
            lines += [f"- **{f.title}.** {f.statement}" for f in items]
            lines.append("")

    if verified.caveats:
        lines += ["## Caveats", ""]
        lines += [f"- {c}" for c in verified.caveats]
        lines.append("")

    if verified.rejected or verified.headline_issue:
        lines += ["## Rejected by fact-check", ""]
        if verified.headline_issue:
            lines.append(f"- Headline: {verified.headline_issue}")
        lines += [f"- _{f.title}_: {reason}" for f, reason in verified.rejected]
        lines.append("")

    return "\n".join(lines)


def save_brief(
    reports_dir: Path, raw: InsightsBrief, verified: VerifiedBrief, meta: BriefMetadata
) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": asdict(meta),
        "raw": raw.model_dump(),
        "accepted": [f.model_dump() for f in verified.accepted],
        "rejected": [{"finding": f.model_dump(), "reason": r} for f, r in verified.rejected],
        "headline_issue": verified.headline_issue,
    }
    (reports_dir / "latest_brief.json").write_text(json.dumps(payload, indent=2) + "\n")
    path = reports_dir / "latest_brief.md"
    path.write_text(render_markdown(verified, meta))
    return path
