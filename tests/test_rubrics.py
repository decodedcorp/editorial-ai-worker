"""Tests for the adaptive rubric system: classifier, registry, and prompt integration.

All tests use pure functions and data structures -- no mocking needed.
"""

import pytest

from editorial_ai.rubrics import (
    ContentType,
    RubricConfig,
    RubricCriterion,
    RUBRIC_REGISTRY,
    classify_content_type,
    get_rubric,
)
from editorial_ai.prompts.review import build_review_prompt


# ---------------------------------------------------------------------------
# Classifier tests
# ---------------------------------------------------------------------------


class TestClassifyContentType:
    def test_classify_fashion_keyword(self) -> None:
        assert classify_content_type("summer fashion") == ContentType.FASHION_MAGAZINE

    def test_classify_tech_keyword(self) -> None:
        assert classify_content_type("AI tools for developers") == ContentType.TECH_BLOG

    def test_classify_lifestyle_keyword(self) -> None:
        assert classify_content_type("home decor trends") == ContentType.LIFESTYLE

    def test_classify_default_fallback(self) -> None:
        """Unknown keywords default to FASHION_MAGAZINE (fashion-first pipeline)."""
        assert classify_content_type("random stuff") == ContentType.FASHION_MAGAZINE

    def test_classify_with_curated_topics(self) -> None:
        """Keyword doesn't match but curated topic related_keywords do."""
        topics = [
            {
                "keyword": "some topic",
                "related_keywords": ["blockchain fundamentals"],
            }
        ]
        result = classify_content_type("something unrelated", topics)
        assert result == ContentType.TECH_BLOG

    def test_classify_case_insensitive(self) -> None:
        assert classify_content_type("FASHION Week") == ContentType.FASHION_MAGAZINE
        assert classify_content_type("Machine Learning") == ContentType.TECH_BLOG


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_get_rubric_fashion(self) -> None:
        rubric = get_rubric(ContentType.FASHION_MAGAZINE)
        assert rubric.content_type == ContentType.FASHION_MAGAZINE
        assert len(rubric.criteria) == 5
        names = [c.name for c in rubric.criteria]
        assert "visual_appeal" in names
        assert "trend_relevance" in names

    def test_get_rubric_tech(self) -> None:
        rubric = get_rubric(ContentType.TECH_BLOG)
        assert rubric.content_type == ContentType.TECH_BLOG
        assert len(rubric.criteria) == 4
        names = [c.name for c in rubric.criteria]
        assert "technical_depth" in names

    def test_get_rubric_lifestyle(self) -> None:
        rubric = get_rubric(ContentType.LIFESTYLE)
        assert len(rubric.criteria) == 4
        names = [c.name for c in rubric.criteria]
        assert "engagement" in names

    def test_get_rubric_unknown_fallback(self) -> None:
        """DEFAULT type returns fashion-equivalent rubric."""
        rubric = get_rubric(ContentType.DEFAULT)
        assert rubric.content_type == ContentType.DEFAULT
        assert len(rubric.criteria) == 5  # same as fashion

    def test_all_content_types_in_registry(self) -> None:
        for ct in ContentType:
            assert ct in RUBRIC_REGISTRY

    def test_tech_fact_accuracy_higher_weight(self) -> None:
        rubric = get_rubric(ContentType.TECH_BLOG)
        fact_acc = next(c for c in rubric.criteria if c.name == "fact_accuracy")
        assert fact_acc.weight == 1.2


# ---------------------------------------------------------------------------
# Prompt integration tests
# ---------------------------------------------------------------------------


class TestPromptIntegration:
    def test_build_review_prompt_with_rubric(self) -> None:
        """Rubric-enabled prompt contains dynamic criteria from config."""
        rubric = get_rubric(ContentType.TECH_BLOG)
        prompt = build_review_prompt("{}", "[]", rubric_config=rubric)
        assert "technical_depth" in prompt.lower() or "기술적 깊이" in prompt
        assert "가중치: 1.2" in prompt  # fact_accuracy weight
        assert "기술 블로그" in prompt  # prompt_additions

    def test_build_review_prompt_backward_compat(self) -> None:
        """None rubric produces original prompt text."""
        prompt = build_review_prompt("{}", "[]")
        assert "hallucination" in prompt
        assert "fact_accuracy" in prompt
        assert "content_completeness" in prompt
        # Original prompt uses "패션 매거진 편집장"
        assert "패션 매거진 편집장" in prompt

    def test_rubric_prompt_contains_all_criteria(self) -> None:
        """All criterion names from rubric appear in the generated prompt."""
        rubric = get_rubric(ContentType.FASHION_MAGAZINE)
        prompt = build_review_prompt("{}", "[]", rubric_config=rubric)
        for criterion in rubric.criteria:
            assert criterion.name in prompt

    def test_rubric_prompt_contains_prompt_additions(self) -> None:
        rubric = get_rubric(ContentType.LIFESTYLE)
        prompt = build_review_prompt("{}", "[]", rubric_config=rubric)
        assert "독자 공감" in prompt
