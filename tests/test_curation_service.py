"""Unit tests for CurationService with mocked Gemini API responses.

All tests use mocked google-genai client — no real API calls are made.
Follows project test conventions from tests/test_services.py.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import errors

from editorial_ai.models.curation import CuratedTopic, CurationResult
from editorial_ai.services.curation_service import CurationService, _strip_markdown_fences

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_RESEARCH_TEXT = """
2025 S/S 시즌, '발레코어(Balletcore)' 트렌드가 다시 주목받고 있습니다.
Miu Miu와 Sandy Liang의 런웨이에서 튤 스커트와 발레 플랫이 등장했으며,
제니(JENNIE)와 해인(Hae-in)이 공항 패션에서 발레코어 룩을 선보였습니다.
관련 키워드: 튤 스커트, 발레 플랫, 리본 디테일, 파스텔 톤, 로맨틱 미니멀리즘
"""

SAMPLE_TOPIC_JSON = json.dumps(
    {
        "keyword": "발레코어",
        "trend_background": "발레코어 트렌드가 2025 S/S에 재부상",
        "related_keywords": ["튤 스커트", "발레 플랫", "리본 디테일"],
        "celebrities": [
            {"name": "제니", "relevance": "공항 패션에서 발레코어 착용"},
            {"name": "해인", "relevance": "드라마 출연 시 발레코어 스타일링"},
        ],
        "brands_products": [
            {"name": "Miu Miu", "relevance": "런웨이에서 발레코어 컬렉션 발표"},
            {"name": "Sandy Liang", "relevance": "발레 플랫 시그니처 아이템"},
        ],
        "seasonality": "S/S 2025",
        "relevance_score": 0.85,
    },
    ensure_ascii=False,
)

SAMPLE_SUBTOPICS_JSON = json.dumps(
    ["튤 스커트 스타일링", "발레 플랫 트렌드", "리본 디테일 액세서리", "파스텔 톤 코디", "로맨틱 미니멀리즘"],
    ensure_ascii=False,
)

LOW_RELEVANCE_TOPIC_JSON = json.dumps(
    {
        "keyword": "파스텔 톤",
        "trend_background": "파스텔 톤 간접 관련",
        "related_keywords": [],
        "celebrities": [],
        "brands_products": [],
        "seasonality": "year-round",
        "relevance_score": 0.4,
    },
    ensure_ascii=False,
)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_response(
    text: str,
    *,
    grounding_chunks: list | None = None,
    has_metadata: bool = True,
) -> MagicMock:
    """Create a mock GenerateContentResponse."""
    response = MagicMock()
    response.text = text

    candidate = MagicMock()
    if has_metadata and grounding_chunks is not None:
        metadata = MagicMock()
        metadata.grounding_chunks = grounding_chunks
        candidate.grounding_metadata = metadata
    elif not has_metadata:
        candidate.grounding_metadata = None
    else:
        metadata = MagicMock()
        metadata.grounding_chunks = []
        candidate.grounding_metadata = metadata

    response.candidates = [candidate]
    return response


def _mock_grounding_chunks() -> list[MagicMock]:
    """Create mock grounding chunks with web sources."""
    chunks = []
    for url, title in [
        ("https://vogue.co.kr/balletcore-2025", "Vogue Korea - 발레코어"),
        ("https://elle.co.kr/miumiu-ss25", "Elle Korea - Miu Miu SS25"),
    ]:
        chunk = MagicMock()
        chunk.web.uri = url
        chunk.web.title = title
        chunks.append(chunk)
    return chunks


def _build_mock_client() -> MagicMock:
    """Build a mock genai.Client with async generate_content."""
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestResearchTrend:
    async def test_returns_text_and_sources(self) -> None:
        """research_trend returns (text, sources) with correct source extraction."""
        client = _build_mock_client()
        chunks = _mock_grounding_chunks()
        client.aio.models.generate_content.return_value = _mock_response(
            SAMPLE_RESEARCH_TEXT, grounding_chunks=chunks
        )

        service = CurationService(client, relevance_threshold=0.6)
        text, sources = await service.research_trend("발레코어")

        assert text == SAMPLE_RESEARCH_TEXT
        assert len(sources) == 2
        assert sources[0].url == "https://vogue.co.kr/balletcore-2025"
        assert sources[0].title == "Vogue Korea - 발레코어"
        assert sources[1].url == "https://elle.co.kr/miumiu-ss25"

    async def test_empty_grounding_returns_empty_sources(self) -> None:
        """When grounding_metadata is None, returns empty sources list."""
        client = _build_mock_client()
        client.aio.models.generate_content.return_value = _mock_response(
            SAMPLE_RESEARCH_TEXT, has_metadata=False
        )

        service = CurationService(client)
        text, sources = await service.research_trend("발레코어")

        assert text == SAMPLE_RESEARCH_TEXT
        assert sources == []


class TestExpandSubtopics:
    async def test_returns_capped_list(self) -> None:
        """Subtopics are parsed from JSON and capped at 7."""
        client = _build_mock_client()
        client.aio.models.generate_content.return_value = _mock_response(SAMPLE_SUBTOPICS_JSON)

        service = CurationService(client)
        subtopics = await service.expand_subtopics("발레코어", SAMPLE_RESEARCH_TEXT)

        assert isinstance(subtopics, list)
        assert len(subtopics) == 5
        assert "튤 스커트 스타일링" in subtopics
        assert len(subtopics) <= 7


class TestExtractTopic:
    async def test_valid_json(self) -> None:
        """CuratedTopic is correctly parsed from mock JSON response."""
        client = _build_mock_client()
        client.aio.models.generate_content.return_value = _mock_response(SAMPLE_TOPIC_JSON)

        service = CurationService(client)
        sources = [
            MagicMock(url="https://example.com", title="Example"),
        ]
        # Need actual GroundingSource objects
        from editorial_ai.models.curation import GroundingSource

        sources = [GroundingSource(url="https://example.com", title="Example")]

        topic = await service.extract_topic("발레코어", SAMPLE_RESEARCH_TEXT, sources)

        assert isinstance(topic, CuratedTopic)
        assert topic.keyword == "발레코어"
        assert topic.relevance_score == 0.85
        assert len(topic.celebrities) == 2
        assert len(topic.brands_products) == 2
        # Sources should be overridden with the passed-in sources
        assert len(topic.sources) == 1
        assert topic.sources[0].url == "https://example.com"

    async def test_markdown_fence_fallback(self) -> None:
        """When response has ```json fences, they are stripped and parsing succeeds."""
        client = _build_mock_client()
        fenced_json = f"```json\n{SAMPLE_TOPIC_JSON}\n```"
        client.aio.models.generate_content.return_value = _mock_response(fenced_json)

        service = CurationService(client)
        from editorial_ai.models.curation import GroundingSource

        sources = [GroundingSource(url="https://example.com", title="Example")]

        topic = await service.extract_topic("발레코어", SAMPLE_RESEARCH_TEXT, sources)

        assert isinstance(topic, CuratedTopic)
        assert topic.keyword == "발레코어"
        assert topic.low_quality is False


class TestCurateSeed:
    async def test_end_to_end(self) -> None:
        """Full pipeline: mock all API calls, verify CurationResult."""
        client = _build_mock_client()
        chunks = _mock_grounding_chunks()

        # Side effects for sequential calls:
        # 1. research_trend (seed) — grounded research
        # 2. expand_subtopics — JSON array
        # 3. extract_topic (seed) — structured JSON
        # 4. research_trend (sub-topic 1) — grounded research
        # 5. extract_topic (sub-topic 1) — structured JSON
        sub_topic_json = json.dumps(
            {
                "keyword": "튤 스커트 스타일링",
                "trend_background": "튤 스커트가 데일리 룩으로 확장",
                "related_keywords": ["튤", "스커트"],
                "celebrities": [{"name": "제니", "relevance": "착용"}],
                "brands_products": [{"name": "Miu Miu", "relevance": "주력 아이템"}],
                "seasonality": "S/S 2025",
                "relevance_score": 0.75,
            },
            ensure_ascii=False,
        )

        # Only 1 subtopic to keep test simple
        one_subtopic_json = json.dumps(["튤 스커트 스타일링"], ensure_ascii=False)

        client.aio.models.generate_content.side_effect = [
            _mock_response(SAMPLE_RESEARCH_TEXT, grounding_chunks=chunks),  # research_trend(seed)
            _mock_response(one_subtopic_json),  # expand_subtopics
            _mock_response(SAMPLE_TOPIC_JSON),  # extract_topic(seed)
            _mock_response(SAMPLE_RESEARCH_TEXT, grounding_chunks=chunks),  # research_trend(sub)
            _mock_response(sub_topic_json),  # extract_topic(sub)
        ]

        service = CurationService(client, relevance_threshold=0.6)
        result = await service.curate_seed("발레코어")

        assert isinstance(result, CurationResult)
        assert result.seed_keyword == "발레코어"
        assert result.total_generated == 2
        assert result.total_filtered == 2
        assert len(result.topics) == 2

    async def test_filters_low_relevance(self) -> None:
        """Topics with relevance_score < 0.6 are excluded from final result."""
        client = _build_mock_client()
        chunks = _mock_grounding_chunks()

        one_subtopic_json = json.dumps(["파스텔 톤"], ensure_ascii=False)

        client.aio.models.generate_content.side_effect = [
            _mock_response(SAMPLE_RESEARCH_TEXT, grounding_chunks=chunks),  # research_trend(seed)
            _mock_response(one_subtopic_json),  # expand_subtopics
            _mock_response(SAMPLE_TOPIC_JSON),  # extract_topic(seed) — 0.85
            _mock_response(SAMPLE_RESEARCH_TEXT, grounding_chunks=chunks),  # research_trend(sub)
            _mock_response(LOW_RELEVANCE_TOPIC_JSON),  # extract_topic(sub) — 0.4
        ]

        service = CurationService(client, relevance_threshold=0.6)
        result = await service.curate_seed("발레코어")

        assert result.total_generated == 2
        assert result.total_filtered == 1  # only the 0.85 topic passes
        assert len(result.topics) == 1
        assert result.topics[0].relevance_score == 0.85

    async def test_skips_failed_subtopic(self) -> None:
        """When a sub-topic's curate_topic raises, it's skipped."""
        client = _build_mock_client()
        chunks = _mock_grounding_chunks()

        one_subtopic_json = json.dumps(["실패할 키워드"], ensure_ascii=False)

        client.aio.models.generate_content.side_effect = [
            _mock_response(SAMPLE_RESEARCH_TEXT, grounding_chunks=chunks),  # research_trend(seed)
            _mock_response(one_subtopic_json),  # expand_subtopics
            _mock_response(SAMPLE_TOPIC_JSON),  # extract_topic(seed)
            # research_trend for sub-topic fails with all retries exhausted
            errors.ServerError(500, {"error": "API overloaded"}),
            errors.ServerError(500, {"error": "API overloaded"}),
            errors.ServerError(500, {"error": "API overloaded"}),
        ]

        service = CurationService(client, relevance_threshold=0.6)
        result = await service.curate_seed("발레코어")

        # Seed topic should still be present, failed sub-topic skipped
        assert result.total_generated == 1
        assert len(result.topics) == 1
        assert result.topics[0].keyword == "발레코어"


class TestRetryOnApiError:
    async def test_retry_succeeds_on_second_attempt(self) -> None:
        """When first API call raises ClientError, tenacity retries and succeeds."""
        client = _build_mock_client()
        chunks = _mock_grounding_chunks()

        # First call fails, second succeeds
        client.aio.models.generate_content.side_effect = [
            errors.ClientError(429, {"error": "Rate limited"}),
            _mock_response(SAMPLE_RESEARCH_TEXT, grounding_chunks=chunks),
        ]

        service = CurationService(client)
        # Override retry wait to zero on the decorated method to avoid sleep
        original_wait = service.research_trend.retry.wait  # type: ignore[attr-defined]
        service.research_trend.retry.wait = lambda *a, **kw: 0  # type: ignore[attr-defined]
        try:
            text, sources = await service.research_trend("발레코어")
        finally:
            service.research_trend.retry.wait = original_wait  # type: ignore[attr-defined]

        assert text == SAMPLE_RESEARCH_TEXT
        assert len(sources) == 2
        # Should have been called twice (1 failure + 1 success)
        assert client.aio.models.generate_content.call_count == 2


class TestStripMarkdownFences:
    def test_strips_json_fences(self) -> None:
        assert _strip_markdown_fences('```json\n{"a": 1}\n```') == '{"a": 1}'

    def test_strips_plain_fences(self) -> None:
        assert _strip_markdown_fences('```\n{"a": 1}\n```') == '{"a": 1}'

    def test_no_fences_unchanged(self) -> None:
        assert _strip_markdown_fences('{"a": 1}') == '{"a": 1}'
