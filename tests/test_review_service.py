"""Unit tests for ReviewService: format validation, LLM evaluation, full evaluate."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from editorial_ai.models.layout import (
    BodyTextBlock,
    CelebFeatureBlock,
    CelebItem,
    CreditEntry,
    CreditsBlock,
    HashtagBarBlock,
    HeadlineBlock,
    HeroBlock,
    MagazineLayout,
    ProductItem,
    ProductShowcaseBlock,
    create_default_template,
)
from editorial_ai.models.review import CriterionResult, ReviewResult
from editorial_ai.services.review_service import ReviewService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_layout_dict() -> dict:
    """Create a valid MagazineLayout dict with body_text block."""
    layout = MagazineLayout(
        keyword="Y2K",
        title="Y2K 트렌드의 귀환",
        blocks=[
            HeroBlock(image_url="https://example.com/hero.jpg", overlay_title="Y2K"),
            HeadlineBlock(text="Y2K 트렌드의 귀환"),
            BodyTextBlock(paragraphs=["첫 번째 단락입니다.", "두 번째 단락입니다."]),
            CelebFeatureBlock(celebs=[CelebItem(name="제니", description="패션 아이콘")]),
            ProductShowcaseBlock(
                products=[ProductItem(name="클래식 플랩 백", brand="Chanel")]
            ),
            HashtagBarBlock(hashtags=["Y2K", "레트로"]),
            CreditsBlock(entries=[CreditEntry(role="AI Editor", name="decoded editorial")]),
        ],
    )
    return layout.model_dump()


def _mock_genai_client(response_text: str) -> MagicMock:
    """Build mock genai client that returns given text."""
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = response_text
    client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    return client


def _all_pass_review_json() -> str:
    """Build a ReviewResult JSON with all 3 semantic criteria passing."""
    result = ReviewResult(
        passed=True,
        criteria=[
            CriterionResult(
                criterion="hallucination",
                passed=True,
                reason="No fabricated information detected",
                severity="minor",
            ),
            CriterionResult(
                criterion="fact_accuracy",
                passed=True,
                reason="All names and descriptions match curated data",
                severity="minor",
            ),
            CriterionResult(
                criterion="content_completeness",
                passed=True,
                reason="All required elements present",
                severity="minor",
            ),
        ],
        summary="Draft passes all criteria",
        suggestions=[],
    )
    return result.model_dump_json()


def _one_fail_review_json() -> str:
    """Build a ReviewResult JSON with hallucination failing."""
    result = ReviewResult(
        passed=False,
        criteria=[
            CriterionResult(
                criterion="hallucination",
                passed=False,
                reason="Draft mentions brand 'FakeBrand' not in curated data",
                severity="critical",
            ),
            CriterionResult(
                criterion="fact_accuracy",
                passed=True,
                reason="Names match curated data",
                severity="minor",
            ),
            CriterionResult(
                criterion="content_completeness",
                passed=True,
                reason="All required elements present",
                severity="minor",
            ),
        ],
        summary="Hallucination detected",
        suggestions=["Remove FakeBrand reference"],
    )
    return result.model_dump_json()


# ---------------------------------------------------------------------------
# TestValidateFormat
# ---------------------------------------------------------------------------


class TestValidateFormat:
    """Tests for deterministic Pydantic format validation (no LLM)."""

    def setup_method(self) -> None:
        # Client is unused for validate_format (sync, no LLM)
        self.service = ReviewService(client=MagicMock())

    def test_valid_layout_passes(self) -> None:
        draft = _valid_layout_dict()
        result = self.service.validate_format(draft)
        assert result.criterion == "format"
        assert result.passed is True
        assert "valid" in result.reason.lower() or "complete" in result.reason.lower()

    def test_invalid_schema_fails(self) -> None:
        result = self.service.validate_format({"bad": "data"})
        assert result.criterion == "format"
        assert result.passed is False
        assert result.severity == "critical"

    def test_missing_body_text_fails(self) -> None:
        """Layout with no body_text block should fail."""
        layout = MagazineLayout(
            keyword="test",
            title="Test Title",
            blocks=[
                HeroBlock(image_url="https://example.com/hero.jpg"),
                HeadlineBlock(text="Test"),
                HashtagBarBlock(hashtags=["test"]),
            ],
        )
        draft = layout.model_dump()
        result = self.service.validate_format(draft)
        assert result.criterion == "format"
        assert result.passed is False
        assert "body_text" in result.reason.lower()

    def test_empty_title_fails(self) -> None:
        """Layout with empty title should fail."""
        layout = MagazineLayout(
            keyword="test",
            title="",
            blocks=[
                BodyTextBlock(paragraphs=["Some content"]),
            ],
        )
        draft = layout.model_dump()
        result = self.service.validate_format(draft)
        assert result.criterion == "format"
        assert result.passed is False
        assert "title" in result.reason.lower()


# ---------------------------------------------------------------------------
# TestEvaluateWithLLM
# ---------------------------------------------------------------------------


class TestEvaluateWithLLM:
    """Tests for LLM-as-a-Judge evaluation (mocked Gemini client)."""

    @pytest.mark.asyncio
    async def test_llm_evaluation_returns_criteria(self) -> None:
        client = _mock_genai_client(_all_pass_review_json())
        service = ReviewService(client=client)

        criteria = await service.evaluate_with_llm(
            '{"title": "test"}', '[{"keyword": "test"}]'
        )
        assert len(criteria) == 3
        criterion_names = {c.criterion for c in criteria}
        assert criterion_names == {"hallucination", "fact_accuracy", "content_completeness"}

    @pytest.mark.asyncio
    async def test_llm_evaluation_uses_temperature_zero(self) -> None:
        client = _mock_genai_client(_all_pass_review_json())
        service = ReviewService(client=client)

        await service.evaluate_with_llm('{"title": "test"}', '[{"keyword": "test"}]')

        call_kwargs = client.aio.models.generate_content.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config.temperature == 0.0

    @pytest.mark.asyncio
    async def test_llm_evaluation_filters_format_criterion(self) -> None:
        """If LLM returns a format criterion, it should be filtered out."""
        result = ReviewResult(
            passed=True,
            criteria=[
                CriterionResult(criterion="format", passed=True, reason="ok", severity="minor"),
                CriterionResult(
                    criterion="hallucination", passed=True, reason="ok", severity="minor"
                ),
            ],
            summary="ok",
        )
        client = _mock_genai_client(result.model_dump_json())
        service = ReviewService(client=client)

        criteria = await service.evaluate_with_llm("{}", "[]")
        assert len(criteria) == 1
        assert criteria[0].criterion == "hallucination"


# ---------------------------------------------------------------------------
# TestEvaluate
# ---------------------------------------------------------------------------


class TestEvaluate:
    """Tests for full evaluate() orchestration."""

    @pytest.mark.asyncio
    async def test_all_pass_returns_passed(self) -> None:
        client = _mock_genai_client(_all_pass_review_json())
        service = ReviewService(client=client)

        draft = _valid_layout_dict()
        result = await service.evaluate(draft, [{"keyword": "Y2K"}])

        assert result.passed is True
        assert len(result.criteria) == 4  # 1 format + 3 semantic
        assert all(c.passed for c in result.criteria)

    @pytest.mark.asyncio
    async def test_format_fail_returns_failed(self) -> None:
        client = _mock_genai_client(_all_pass_review_json())
        service = ReviewService(client=client)

        # Invalid draft -- will fail format validation
        result = await service.evaluate({"bad": "data"}, [{"keyword": "test"}])

        assert result.passed is False
        format_criterion = next(c for c in result.criteria if c.criterion == "format")
        assert format_criterion.passed is False

    @pytest.mark.asyncio
    async def test_llm_fail_returns_failed(self) -> None:
        client = _mock_genai_client(_one_fail_review_json())
        service = ReviewService(client=client)

        draft = _valid_layout_dict()
        result = await service.evaluate(draft, [{"keyword": "Y2K"}])

        assert result.passed is False
        hallucination = next(c for c in result.criteria if c.criterion == "hallucination")
        assert hallucination.passed is False

    @pytest.mark.asyncio
    async def test_suggestions_contain_failed_reasons(self) -> None:
        client = _mock_genai_client(_one_fail_review_json())
        service = ReviewService(client=client)

        draft = _valid_layout_dict()
        result = await service.evaluate(draft, [{"keyword": "Y2K"}])

        assert len(result.suggestions) > 0
        assert any("FakeBrand" in s for s in result.suggestions)

    @pytest.mark.asyncio
    async def test_summary_mentions_failed_criteria(self) -> None:
        client = _mock_genai_client(_one_fail_review_json())
        service = ReviewService(client=client)

        draft = _valid_layout_dict()
        result = await service.evaluate(draft, [{"keyword": "Y2K"}])

        assert "hallucination" in result.summary.lower()
