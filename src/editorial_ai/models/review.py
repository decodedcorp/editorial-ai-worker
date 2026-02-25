"""Pydantic models for the review agent evaluation output.

ReviewResult captures the complete evaluation from the LLM-as-a-Judge pipeline.
CriterionResult holds per-criterion pass/fail with severity and actionable reason.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CriterionResult(BaseModel):
    """Result for a single evaluation criterion."""

    criterion: Literal["hallucination", "format", "fact_accuracy", "content_completeness"]
    passed: bool
    reason: str  # Actionable explanation -- why it passed or failed
    severity: Literal["critical", "major", "minor"] = "major"


class ReviewResult(BaseModel):
    """Complete review evaluation result from LLM-as-a-Judge."""

    passed: bool  # Overall pass/fail (computed by service, not LLM)
    criteria: list[CriterionResult]
    summary: str  # Brief overall assessment
    suggestions: list[str] = Field(default_factory=list)  # Improvement suggestions
