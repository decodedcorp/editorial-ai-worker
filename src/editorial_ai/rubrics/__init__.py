"""Adaptive rubric system for content-type-specific review evaluation."""

from editorial_ai.rubrics.classifier import classify_content_type
from editorial_ai.rubrics.registry import (
    RUBRIC_REGISTRY,
    ContentType,
    RubricConfig,
    RubricCriterion,
    get_rubric,
)

__all__ = [
    "ContentType",
    "RubricConfig",
    "RubricCriterion",
    "RUBRIC_REGISTRY",
    "classify_content_type",
    "get_rubric",
]
