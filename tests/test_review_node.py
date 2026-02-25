"""Tests for the review LangGraph node.

All tests mock ReviewService -- no real LLM calls.
Verifies state reads/writes, pass/fail routing, escalation, and error handling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from editorial_ai.models.layout import create_default_template
from editorial_ai.models.review import CriterionResult, ReviewResult
from editorial_ai.nodes.review import review_node

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PATCH_SERVICE = "editorial_ai.nodes.review.ReviewService"
_PATCH_CLIENT = "editorial_ai.nodes.review.get_genai_client"


def _base_state(**overrides: object) -> dict:
    """Minimal state for review node invocation."""
    state: dict = {
        "curation_input": {"keyword": "Y2K"},
        "curated_topics": [{"keyword": "Y2K", "trend_background": "Y2K revival"}],
        "enriched_contexts": [],
        "current_draft": create_default_template("Y2K", "Y2K Revival").model_dump(),
        "current_draft_id": None,
        "tool_calls_log": [],
        "review_result": None,
        "revision_count": 0,
        "feedback_history": [],
        "admin_decision": None,
        "admin_feedback": None,
        "pipeline_status": "reviewing",
        "error_log": [],
    }
    state.update(overrides)
    return state


def _passing_review() -> ReviewResult:
    return ReviewResult(
        passed=True,
        criteria=[
            CriterionResult(criterion="format", passed=True, reason="OK"),
            CriterionResult(criterion="hallucination", passed=True, reason="OK"),
            CriterionResult(criterion="fact_accuracy", passed=True, reason="OK"),
            CriterionResult(criterion="content_completeness", passed=True, reason="OK"),
        ],
        summary="All criteria passed",
    )


def _failing_review() -> ReviewResult:
    return ReviewResult(
        passed=False,
        criteria=[
            CriterionResult(criterion="format", passed=True, reason="OK"),
            CriterionResult(criterion="hallucination", passed=False, reason="Found fabricated brand", severity="critical"),
            CriterionResult(criterion="fact_accuracy", passed=True, reason="OK"),
            CriterionResult(criterion="content_completeness", passed=True, reason="OK"),
        ],
        summary="Hallucination detected",
        suggestions=["Remove fabricated brand references"],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReviewNodePass:
    @patch(_PATCH_CLIENT, return_value=MagicMock())
    @patch(_PATCH_SERVICE)
    async def test_pass_sets_awaiting_approval(self, MockService, mock_client):
        instance = MockService.return_value
        instance.evaluate = AsyncMock(return_value=_passing_review())
        result = await review_node(_base_state())
        assert result["pipeline_status"] == "awaiting_approval"
        assert result["review_result"]["passed"] is True

    @patch(_PATCH_CLIENT, return_value=MagicMock())
    @patch(_PATCH_SERVICE)
    async def test_pass_does_not_increment_revision_count(self, MockService, mock_client):
        instance = MockService.return_value
        instance.evaluate = AsyncMock(return_value=_passing_review())
        result = await review_node(_base_state())
        assert "revision_count" not in result


class TestReviewNodeFail:
    @patch(_PATCH_CLIENT, return_value=MagicMock())
    @patch(_PATCH_SERVICE)
    async def test_fail_increments_revision_count(self, MockService, mock_client):
        instance = MockService.return_value
        instance.evaluate = AsyncMock(return_value=_failing_review())
        result = await review_node(_base_state(revision_count=0))
        assert result["revision_count"] == 1

    @patch(_PATCH_CLIENT, return_value=MagicMock())
    @patch(_PATCH_SERVICE)
    async def test_fail_appends_feedback_history(self, MockService, mock_client):
        instance = MockService.return_value
        instance.evaluate = AsyncMock(return_value=_failing_review())
        result = await review_node(_base_state())
        assert "feedback_history" in result
        assert len(result["feedback_history"]) == 1
        assert result["feedback_history"][0]["passed"] is False

    @patch(_PATCH_CLIENT, return_value=MagicMock())
    @patch(_PATCH_SERVICE)
    async def test_fail_does_not_set_pipeline_status(self, MockService, mock_client):
        """Non-escalation failure does not set pipeline_status (route_after_review handles)."""
        instance = MockService.return_value
        instance.evaluate = AsyncMock(return_value=_failing_review())
        result = await review_node(_base_state(revision_count=0))
        assert "pipeline_status" not in result


class TestReviewNodeEscalation:
    @patch(_PATCH_CLIENT, return_value=MagicMock())
    @patch(_PATCH_SERVICE)
    async def test_escalation_sets_failed_status(self, MockService, mock_client):
        """revision_count=2 -> becomes 3 -> escalation."""
        instance = MockService.return_value
        instance.evaluate = AsyncMock(return_value=_failing_review())
        result = await review_node(_base_state(revision_count=2))
        assert result["pipeline_status"] == "failed"
        assert result["revision_count"] == 3
        assert len(result["error_log"]) == 1
        assert "Escalation" in result["error_log"][0]

    @patch(_PATCH_CLIENT, return_value=MagicMock())
    @patch(_PATCH_SERVICE)
    async def test_escalation_still_appends_feedback(self, MockService, mock_client):
        """Even on escalation, feedback_history is appended for audit trail."""
        instance = MockService.return_value
        instance.evaluate = AsyncMock(return_value=_failing_review())
        result = await review_node(_base_state(revision_count=2))
        assert "feedback_history" in result
        assert len(result["feedback_history"]) == 1


class TestReviewNodeNoDraft:
    async def test_no_draft_returns_failure(self):
        result = await review_node(_base_state(current_draft=None))
        assert result["review_result"]["passed"] is False
        assert len(result["error_log"]) == 1
        assert "no current_draft" in result["error_log"][0]


class TestReviewNodeServiceError:
    @patch(_PATCH_CLIENT, return_value=MagicMock())
    @patch(_PATCH_SERVICE)
    async def test_service_exception_returns_error(self, MockService, mock_client):
        instance = MockService.return_value
        instance.evaluate = AsyncMock(side_effect=RuntimeError("API timeout"))
        result = await review_node(_base_state())
        assert result["review_result"]["passed"] is False
        assert len(result["error_log"]) == 1
        assert "RuntimeError" in result["error_log"][0]
        assert "API timeout" in result["error_log"][0]
