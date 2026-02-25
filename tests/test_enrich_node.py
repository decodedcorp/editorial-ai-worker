"""Tests for the enrich LangGraph node.

All tests mock enrich_editorial_content -- no real API/DB calls.
Verifies state reads/writes and error handling at the node level.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from editorial_ai.models.layout import MagazineLayout, create_default_template
from editorial_ai.nodes.enrich import enrich_editorial_node

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PATCH_ENRICH = "editorial_ai.nodes.enrich.enrich_editorial_content"


def _sample_layout() -> MagazineLayout:
    return create_default_template("Y2K", "Y2K Revival: 2025 Edition")


def _base_state(**overrides: object) -> dict:
    """Minimal state dict for enrich node invocation."""
    state: dict = {
        "curation_input": {"keyword": "Y2K"},
        "curated_topics": [],
        "enriched_contexts": [],
        "current_draft": _sample_layout().model_dump(),
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEnrichNodeNoDraft:
    async def test_no_current_draft(self) -> None:
        """When current_draft is None, returns error_log entry."""
        result = await enrich_editorial_node(_base_state(current_draft=None))

        assert "error_log" in result
        assert len(result["error_log"]) == 1
        assert "no current_draft" in result["error_log"][0]
        assert "current_draft" not in result


class TestEnrichNodeSuccess:
    @patch(_PATCH_ENRICH)
    async def test_enriches_draft(self, mock_enrich: AsyncMock) -> None:
        """Successful enrichment updates current_draft in state."""
        enriched_layout = _sample_layout()
        enriched_layout.title = "Y2K Revival: Enriched Edition"
        mock_enrich.return_value = enriched_layout

        result = await enrich_editorial_node(_base_state())

        assert "current_draft" in result
        assert result["current_draft"]["title"] == "Y2K Revival: Enriched Edition"
        mock_enrich.assert_awaited_once()

    @patch(_PATCH_ENRICH)
    async def test_does_not_change_pipeline_status(self, mock_enrich: AsyncMock) -> None:
        """Enrich node is transparent -- does not modify pipeline_status."""
        mock_enrich.return_value = _sample_layout()

        result = await enrich_editorial_node(_base_state())

        assert "pipeline_status" not in result


class TestEnrichNodeServiceError:
    @patch(_PATCH_ENRICH)
    async def test_exception_returns_error_log(self, mock_enrich: AsyncMock) -> None:
        """Service exception returns error_log without crashing."""
        mock_enrich.side_effect = RuntimeError("DB connection failed")

        result = await enrich_editorial_node(_base_state())

        assert "error_log" in result
        assert len(result["error_log"]) == 1
        assert "RuntimeError" in result["error_log"][0]
        assert "DB connection failed" in result["error_log"][0]
        assert "current_draft" not in result
