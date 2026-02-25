"""Tests for the curation LangGraph node.

All tests mock CurationService and get_genai_client — no real API calls.
Verifies state reads/writes and error handling at the node level.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.graph.state import CompiledStateGraph

from editorial_ai.models.curation import (
    BrandReference,
    CelebReference,
    CuratedTopic,
    CurationResult,
    GroundingSource,
)
from editorial_ai.nodes.curation import curation_node


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_TOPICS = [
    CuratedTopic(
        keyword="Y2K",
        trend_background="Y2K 패션이 2025년에 재부상",
        related_keywords=["로우라이즈", "미니스커트", "버터플라이"],
        celebrities=[CelebReference(name="제니", relevance="Y2K 룩 착용")],
        brands_products=[BrandReference(name="Miu Miu", relevance="Y2K 컬렉션")],
        seasonality="S/S 2025",
        sources=[GroundingSource(url="https://example.com/y2k", title="Y2K Trend")],
        relevance_score=0.9,
    ),
    CuratedTopic(
        keyword="로우라이즈",
        trend_background="로우라이즈 진이 데일리 룩으로 확산",
        related_keywords=["데님", "와이드"],
        celebrities=[CelebReference(name="해인", relevance="공항 패션")],
        brands_products=[BrandReference(name="Acne Studios", relevance="시그니처 데님")],
        seasonality="S/S 2025",
        sources=[GroundingSource(url="https://example.com/lowrise", title="Low Rise")],
        relevance_score=0.8,
    ),
    CuratedTopic(
        keyword="버터플라이 액세서리",
        trend_background="버터플라이 모티프 액세서리 인기",
        related_keywords=["헤어클립", "목걸이"],
        celebrities=[],
        brands_products=[],
        seasonality="year-round",
        sources=[],
        relevance_score=0.7,
    ),
]


def _sample_curation_result() -> CurationResult:
    return CurationResult(
        seed_keyword="Y2K",
        topics=SAMPLE_TOPICS,
        total_generated=5,
        total_filtered=3,
    )


def _base_state(**overrides: object) -> dict:
    """Minimal state dict for curation node invocation."""
    state: dict = {
        "curation_input": {"keyword": "Y2K"},
        "curated_topics": [],
        "enriched_contexts": [],
        "current_draft": None,
        "current_draft_id": None,
        "tool_calls_log": [],
        "review_result": None,
        "revision_count": 0,
        "feedback_history": [],
        "admin_decision": None,
        "admin_feedback": None,
        "pipeline_status": "curating",
        "error_log": [],
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

_PATCH_SERVICE = "editorial_ai.nodes.curation.CurationService"
_PATCH_CLIENT = "editorial_ai.nodes.curation.get_genai_client"


class TestCurationNodeSuccess:
    @patch(_PATCH_CLIENT)
    @patch(_PATCH_SERVICE)
    async def test_returns_sourcing_with_topics(
        self, mock_service_cls: MagicMock, mock_client_fn: MagicMock
    ) -> None:
        """Successful curation sets pipeline_status='sourcing' and curated_topics."""
        mock_instance = MagicMock()
        mock_instance.curate_seed = AsyncMock(return_value=_sample_curation_result())
        mock_service_cls.return_value = mock_instance

        result = await curation_node(_base_state())

        assert result["pipeline_status"] == "sourcing"
        assert isinstance(result["curated_topics"], list)
        assert len(result["curated_topics"]) == 3
        # Each topic should be a dict (model_dump output)
        for topic in result["curated_topics"]:
            assert isinstance(topic, dict)
            assert "keyword" in topic
        mock_instance.curate_seed.assert_awaited_once_with("Y2K")

    @patch(_PATCH_CLIENT)
    @patch(_PATCH_SERVICE)
    async def test_topics_are_dicts_with_expected_fields(
        self, mock_service_cls: MagicMock, mock_client_fn: MagicMock
    ) -> None:
        """curated_topics contain model_dump output with all CuratedTopic fields."""
        mock_instance = MagicMock()
        mock_instance.curate_seed = AsyncMock(return_value=_sample_curation_result())
        mock_service_cls.return_value = mock_instance

        result = await curation_node(_base_state())

        first_topic = result["curated_topics"][0]
        assert first_topic["keyword"] == "Y2K"
        assert first_topic["relevance_score"] == 0.9
        assert "celebrities" in first_topic
        assert "brands_products" in first_topic


class TestCurationNodeMissingKeyword:
    async def test_empty_curation_input(self) -> None:
        """Empty curation_input returns failed status with error."""
        result = await curation_node(_base_state(curation_input={}))

        assert result["pipeline_status"] == "failed"
        assert len(result["error_log"]) == 1
        assert "no seed keyword" in result["error_log"][0]

    async def test_missing_curation_input(self) -> None:
        """Missing curation_input key returns failed status."""
        state = _base_state()
        state.pop("curation_input", None)
        result = await curation_node(state)

        assert result["pipeline_status"] == "failed"
        assert "error_log" in result

    async def test_does_not_call_service(self) -> None:
        """When keyword is missing, CurationService is never instantiated."""
        with patch(_PATCH_SERVICE) as mock_service_cls, patch(_PATCH_CLIENT):
            await curation_node(_base_state(curation_input={}))
            mock_service_cls.assert_not_called()


class TestCurationNodeApiFailure:
    @patch(_PATCH_CLIENT)
    @patch(_PATCH_SERVICE)
    async def test_exception_returns_failed(
        self, mock_service_cls: MagicMock, mock_client_fn: MagicMock
    ) -> None:
        """API exception sets pipeline_status='failed' with error_log."""
        mock_instance = MagicMock()
        mock_instance.curate_seed = AsyncMock(
            side_effect=RuntimeError("API connection timeout")
        )
        mock_service_cls.return_value = mock_instance

        result = await curation_node(_base_state())

        assert result["pipeline_status"] == "failed"
        assert len(result["error_log"]) == 1
        assert "RuntimeError" in result["error_log"][0]
        assert "API connection timeout" in result["error_log"][0]
        assert result["curated_topics"] == []


class TestCurationNodeEmptyResults:
    @patch(_PATCH_CLIENT)
    @patch(_PATCH_SERVICE)
    async def test_empty_topics_is_valid(
        self, mock_service_cls: MagicMock, mock_client_fn: MagicMock
    ) -> None:
        """Empty topics (all filtered) is valid — returns sourcing, not failed."""
        empty_result = CurationResult(
            seed_keyword="Y2K",
            topics=[],
            total_generated=5,
            total_filtered=0,
        )
        mock_instance = MagicMock()
        mock_instance.curate_seed = AsyncMock(return_value=empty_result)
        mock_service_cls.return_value = mock_instance

        result = await curation_node(_base_state())

        assert result["pipeline_status"] == "sourcing"
        assert result["curated_topics"] == []


class TestGraphWithRealCurationNode:
    def test_graph_compilation_with_real_curation_node(self) -> None:
        """build_graph() without overrides compiles with async curation node."""
        from editorial_ai.graph import build_graph

        compiled = build_graph()
        assert isinstance(compiled, CompiledStateGraph)
