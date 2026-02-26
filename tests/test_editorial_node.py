"""Tests for the editorial LangGraph node.

All tests mock EditorialService and get_genai_client -- no real API calls.
Verifies state reads/writes and error handling at the node level.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from editorial_ai.models.layout import MagazineLayout, create_default_template
from editorial_ai.nodes.editorial import editorial_node

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PATCH_SERVICE = "editorial_ai.nodes.editorial.EditorialService"
_PATCH_CLIENT = "editorial_ai.nodes.editorial.get_genai_client"


def _sample_layout() -> MagazineLayout:
    return create_default_template("Y2K", "Y2K Revival: 2025 Edition")


def _base_state(**overrides: object) -> dict:
    """Minimal state dict for editorial node invocation."""
    state: dict = {
        "curation_input": {"keyword": "Y2K"},
        "curated_topics": [
            {
                "keyword": "Y2K",
                "trend_background": "Y2K 패션이 2025년에 재부상",
                "related_keywords": ["로우라이즈", "미니스커트"],
                "celebrities": [],
                "brands_products": [],
                "seasonality": "S/S 2025",
                "sources": [],
                "relevance_score": 0.9,
            },
        ],
        "enriched_contexts": [],
        "current_draft": None,
        "current_draft_id": None,
        "tool_calls_log": [],
        "review_result": None,
        "revision_count": 0,
        "feedback_history": [],
        "admin_decision": None,
        "admin_feedback": None,
        "pipeline_status": "drafting",
        "error_log": [],
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEditorialNodeSuccess:
    @patch(_PATCH_CLIENT)
    @patch(_PATCH_SERVICE)
    async def test_returns_reviewing_with_draft(
        self, mock_service_cls: MagicMock, mock_client_fn: MagicMock
    ) -> None:
        """Successful editorial sets pipeline_status='reviewing' and current_draft."""
        mock_instance = MagicMock()
        mock_instance.create_editorial = AsyncMock(
            return_value=(_sample_layout(), b"fake_image_bytes")
        )
        mock_service_cls.return_value = mock_instance

        result = await editorial_node(_base_state())

        assert result["pipeline_status"] == "reviewing"
        assert result["current_draft"] is not None
        assert isinstance(result["current_draft"], dict)
        assert result["current_draft"]["keyword"] == "Y2K"
        assert result["layout_image_base64"] is not None
        mock_instance.create_editorial.assert_awaited_once()


class TestEditorialNodeNoTopics:
    async def test_empty_curated_topics(self) -> None:
        """Empty curated_topics returns failed status with error."""
        result = await editorial_node(_base_state(curated_topics=[]))

        assert result["pipeline_status"] == "failed"
        assert len(result["error_log"]) == 1
        assert "no curated_topics" in result["error_log"][0]
        assert result["current_draft"] is None

    async def test_missing_curated_topics(self) -> None:
        """Missing curated_topics key returns failed status."""
        state = _base_state()
        state.pop("curated_topics", None)
        result = await editorial_node(state)

        assert result["pipeline_status"] == "failed"
        assert result["current_draft"] is None


class TestEditorialNodeServiceError:
    @patch(_PATCH_CLIENT)
    @patch(_PATCH_SERVICE)
    async def test_exception_returns_failed(
        self, mock_service_cls: MagicMock, mock_client_fn: MagicMock
    ) -> None:
        """Service exception sets pipeline_status='failed' with error_log."""
        mock_instance = MagicMock()
        mock_instance.create_editorial = AsyncMock(
            side_effect=RuntimeError("Gemini API timeout")
        )
        mock_service_cls.return_value = mock_instance

        result = await editorial_node(_base_state())

        assert result["pipeline_status"] == "failed"
        assert len(result["error_log"]) == 1
        assert "RuntimeError" in result["error_log"][0]
        assert "Gemini API timeout" in result["error_log"][0]
        assert result["current_draft"] is None


class TestEditorialNodeFeedbackInjection:
    @patch(_PATCH_CLIENT)
    @patch(_PATCH_SERVICE)
    async def test_editorial_node_passes_feedback_to_service(
        self, mock_service_cls: MagicMock, mock_client_fn: MagicMock
    ) -> None:
        """When feedback_history is present, node passes it to create_editorial."""
        mock_instance = MagicMock()
        mock_instance.create_editorial = AsyncMock(
            return_value=(_sample_layout(), b"fake_image_bytes")
        )
        mock_service_cls.return_value = mock_instance

        feedback = [
            {
                "criteria": [
                    {"criterion": "hallucination", "passed": False, "reason": "unverified claim"},
                ],
                "suggestions": ["Remove unverified claims"],
            }
        ]
        draft = {"title": "Old Draft Title", "keyword": "Y2K", "blocks": []}

        result = await editorial_node(
            _base_state(feedback_history=feedback, current_draft=draft)
        )

        assert result["pipeline_status"] == "reviewing"
        call_kwargs = mock_instance.create_editorial.call_args
        assert call_kwargs.kwargs["feedback_history"] == feedback
        assert call_kwargs.kwargs["previous_draft"] == draft

    @patch(_PATCH_CLIENT)
    @patch(_PATCH_SERVICE)
    async def test_editorial_node_no_feedback_first_run(
        self, mock_service_cls: MagicMock, mock_client_fn: MagicMock
    ) -> None:
        """First run (empty feedback_history) passes feedback_history=None."""
        mock_instance = MagicMock()
        mock_instance.create_editorial = AsyncMock(
            return_value=(_sample_layout(), None)
        )
        mock_service_cls.return_value = mock_instance

        result = await editorial_node(_base_state(feedback_history=[]))

        assert result["pipeline_status"] == "reviewing"
        call_kwargs = mock_instance.create_editorial.call_args
        assert call_kwargs.kwargs["feedback_history"] is None
        assert call_kwargs.kwargs["previous_draft"] is None


class TestEditorialNodeTrendContext:
    @patch(_PATCH_CLIENT)
    @patch(_PATCH_SERVICE)
    async def test_builds_trend_context_from_multiple_topics(
        self, mock_service_cls: MagicMock, mock_client_fn: MagicMock
    ) -> None:
        """Node concatenates multiple topic backgrounds and keywords into trend_context."""
        mock_instance = MagicMock()
        mock_instance.create_editorial = AsyncMock(
            return_value=(_sample_layout(), None)
        )
        mock_service_cls.return_value = mock_instance

        state = _base_state(
            curated_topics=[
                {
                    "keyword": "Y2K",
                    "trend_background": "Y2K fashion revival",
                    "related_keywords": ["low-rise", "butterfly"],
                    "celebrities": [],
                    "brands_products": [],
                    "sources": [],
                    "relevance_score": 0.9,
                },
                {
                    "keyword": "Quiet Luxury",
                    "trend_background": "Minimalist luxury trending",
                    "related_keywords": ["cashmere", "neutral"],
                    "celebrities": [],
                    "brands_products": [],
                    "sources": [],
                    "relevance_score": 0.8,
                },
            ],
        )

        await editorial_node(state)

        # Verify the trend_context passed to create_editorial
        call_args = mock_instance.create_editorial.call_args
        keyword_arg = call_args[0][0]
        trend_context_arg = call_args[0][1]

        assert keyword_arg == "Y2K"  # first topic keyword
        assert "Y2K fashion revival" in trend_context_arg
        assert "Minimalist luxury trending" in trend_context_arg
        assert "low-rise" in trend_context_arg
        assert "cashmere" in trend_context_arg
