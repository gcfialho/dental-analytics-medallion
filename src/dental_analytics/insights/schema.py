"""Structured output contract for the insights brief."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Finding(BaseModel):
    kind: Literal["observation", "recommendation"]
    title: str = Field(description="Short headline, at most 12 words.")
    statement: str = Field(
        description=("One or two sentences. Every number must be copied from the `display` value of a cited fact.")
    )
    metric_ids: list[str] = Field(description="Ids of every fact the statement relies on.")


class InsightsBrief(BaseModel):
    headline: str = Field(description="One-sentence summary. Numbers must come from the facts.")
    findings: list[Finding]
    caveats: list[str] = Field(description="Data limitations a reader must know. No numbers needed.")
