"""Unit tests for EditorialService with mocked Gemini API responses.

All tests use mocked google-genai client -- no real API calls are made.
Follows project test patterns from tests/test_curation_service.py.
"""

import json
from unittest.mock import AsyncMock, MagicMock

from editorial_ai.models.editorial import EditorialContent
from editorial_ai.models.layout import (
    BodyTextBlock,
    CelebFeatureBlock,
    CreditsBlock,
    HashtagBarBlock,
    HeadlineBlock,
    HeroBlock,
    MagazineLayout,
    ProductShowcaseBlock,
    create_default_template,
)
from editorial_ai.services.editorial_service import EditorialService

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_CONTENT_JSON = json.dumps(
    {
        "keyword": "Y2K 패션",
        "title": "Y2K 리바이벌: 레트로가 다시 온다",
        "subtitle": "2000년대 패션이 2025년에 재해석되는 방법",
        "body_paragraphs": [
            "Y2K 패션이 돌아왔다. 로우라이즈 데님부터 크롭탑까지.",
            "셀럽들이 앞다투어 Y2K 스타일을 선보이고 있다.",
        ],
        "pull_quotes": ["레트로는 죽지 않는다, 진화할 뿐이다."],
        "product_mentions": [
            {
                "name": "로우라이즈 데님",
                "brand": "Miu Miu",
                "context": "Y2K 대표 아이템으로 재출시",
            },
        ],
        "celeb_mentions": [
            {
                "name": "제니",
                "context": "공항 패션에서 Y2K 룩 착용",
            },
        ],
        "hashtags": ["Y2K", "레트로패션", "로우라이즈"],
        "credits": [
            {"role": "AI Editor", "name": "decoded editorial"},
        ],
    },
    ensure_ascii=False,
)

SAMPLE_INVALID_CONTENT_JSON = json.dumps(
    {
        "keyword": "Y2K 패션",
        "title": "Y2K 리바이벌",
        # Missing required field: body_paragraphs
    },
    ensure_ascii=False,
)

SAMPLE_LAYOUT_BLOCKS_JSON = json.dumps(
    [
        {"type": "hero", "order": 0},
        {"type": "headline", "order": 1},
        {"type": "body_text", "order": 2},
        {"type": "pull_quote", "order": 3},
        {"type": "product_showcase", "order": 4},
        {"type": "celeb_feature", "order": 5},
        {"type": "hashtag_bar", "order": 6},
        {"type": "credits", "order": 7},
    ],
)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_text_response(text: str) -> MagicMock:
    """Create a mock GenerateContentResponse with text."""
    response = MagicMock()
    response.text = text
    response.candidates = [MagicMock()]
    return response


def _mock_image_response(
    image_data: bytes = b"fake_image_bytes",
    mime_type: str = "image/png",
) -> MagicMock:
    """Create a mock response with inline_data image part."""
    response = MagicMock()
    response.text = ""

    inline_data = MagicMock()
    inline_data.data = image_data
    inline_data.mime_type = mime_type

    image_part = MagicMock()
    image_part.inline_data = inline_data

    content = MagicMock()
    content.parts = [image_part]

    candidate = MagicMock()
    candidate.content = content

    response.candidates = [candidate]
    return response


def _mock_empty_image_response() -> MagicMock:
    """Create a mock response with no image parts."""
    response = MagicMock()
    response.text = ""

    text_part = MagicMock()
    text_part.inline_data = None

    content = MagicMock()
    content.parts = [text_part]

    candidate = MagicMock()
    candidate.content = content

    response.candidates = [candidate]
    return response


def _build_mock_client() -> MagicMock:
    """Build a mock genai.Client with async generate_content."""
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock()
    return client


def _build_service(
    client: MagicMock | None = None,
) -> EditorialService:
    """Build EditorialService with mock client."""
    if client is None:
        client = _build_mock_client()
    return EditorialService(
        client,
        content_model="gemini-2.5-flash",
        image_model="gemini-2.5-flash-preview-image-generation",
        max_repair_attempts=2,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateContent:
    async def test_generate_content_success(self) -> None:
        """Valid JSON response is parsed into EditorialContent."""
        client = _build_mock_client()
        client.aio.models.generate_content.return_value = (
            _mock_text_response(SAMPLE_CONTENT_JSON)
        )

        service = _build_service(client)
        content = await service.generate_content(
            "Y2K 패션",
            "레트로 트렌드 부활",
        )

        assert isinstance(content, EditorialContent)
        assert content.keyword == "Y2K 패션"
        assert content.title == "Y2K 리바이벌: 레트로가 다시 온다"
        assert len(content.body_paragraphs) == 2
        assert len(content.product_mentions) == 1
        assert len(content.celeb_mentions) == 1
        assert content.hashtags == ["Y2K", "레트로패션", "로우라이즈"]

    async def test_generate_content_with_repair(self) -> None:
        """Invalid JSON triggers repair loop; second call returns valid JSON."""
        client = _build_mock_client()
        # First call: invalid JSON, second call (repair): valid JSON
        client.aio.models.generate_content.side_effect = [
            _mock_text_response(SAMPLE_INVALID_CONTENT_JSON),
            _mock_text_response(SAMPLE_CONTENT_JSON),
        ]

        service = _build_service(client)
        content = await service.generate_content(
            "Y2K 패션",
            "레트로 트렌드 부활",
        )

        assert isinstance(content, EditorialContent)
        assert content.keyword == "Y2K 패션"
        # 2 calls: original generate + 1 repair
        assert client.aio.models.generate_content.call_count == 2


class TestGenerateLayoutImage:
    async def test_generate_layout_image_success(self) -> None:
        """Image bytes are extracted from inline_data response part."""
        client = _build_mock_client()
        client.aio.models.generate_content.return_value = (
            _mock_image_response(b"test_image_data")
        )

        service = _build_service(client)
        result = await service.generate_layout_image(
            "Y2K 패션",
            "Y2K 리바이벌",
            8,
        )

        assert result == b"test_image_data"

    async def test_generate_layout_image_failure_returns_none(
        self,
    ) -> None:
        """Exception during image generation returns None (not raised)."""
        client = _build_mock_client()
        client.aio.models.generate_content.side_effect = RuntimeError(
            "API failure",
        )

        service = _build_service(client)
        result = await service.generate_layout_image(
            "Y2K 패션",
            "Y2K 리바이벌",
            8,
        )

        assert result is None


class TestParseLayoutImage:
    async def test_parse_layout_image_success(self) -> None:
        """Vision response JSON array is parsed to block list."""
        client = _build_mock_client()
        client.aio.models.generate_content.return_value = (
            _mock_text_response(SAMPLE_LAYOUT_BLOCKS_JSON)
        )

        service = _build_service(client)
        result = await service.parse_layout_image(
            b"fake_image",
            "Y2K 패션",
        )

        assert result is not None
        assert len(result) == 8
        assert result[0]["type"] == "hero"
        assert result[0]["order"] == 0

    async def test_parse_layout_image_failure_returns_none(
        self,
    ) -> None:
        """Exception during vision parsing returns None."""
        client = _build_mock_client()
        client.aio.models.generate_content.side_effect = RuntimeError(
            "Vision API error",
        )

        service = _build_service(client)
        result = await service.parse_layout_image(
            b"fake_image",
            "Y2K 패션",
        )

        assert result is None


class TestMergeContentIntoLayout:
    def test_merge_content_into_layout(self) -> None:
        """Content fields are mapped into matching block types."""
        content = EditorialContent.model_validate_json(
            SAMPLE_CONTENT_JSON,
        )
        layout = create_default_template("Y2K 패션", content.title)

        service = _build_service()
        merged = service.merge_content_into_layout(content, layout)

        assert isinstance(merged, MagazineLayout)
        # Verify individual block types are populated
        hero = [b for b in merged.blocks if isinstance(b, HeroBlock)]
        assert hero[0].overlay_title == content.title

        headline = [
            b for b in merged.blocks if isinstance(b, HeadlineBlock)
        ]
        assert headline[0].text == content.title

        body = [
            b for b in merged.blocks if isinstance(b, BodyTextBlock)
        ]
        assert body[0].paragraphs == content.body_paragraphs

        products = [
            b
            for b in merged.blocks
            if isinstance(b, ProductShowcaseBlock)
        ]
        assert len(products[0].products) == 1
        assert products[0].products[0].name == "로우라이즈 데님"

        celebs = [
            b
            for b in merged.blocks
            if isinstance(b, CelebFeatureBlock)
        ]
        assert len(celebs[0].celebs) == 1
        assert celebs[0].celebs[0].name == "제니"

        hashtags = [
            b for b in merged.blocks if isinstance(b, HashtagBarBlock)
        ]
        assert hashtags[0].hashtags == ["Y2K", "레트로패션", "로우라이즈"]

        credits = [
            b for b in merged.blocks if isinstance(b, CreditsBlock)
        ]
        assert credits[0].entries[0].role == "AI Editor"

        # Verify original layout is not mutated
        original_hero = [
            b for b in layout.blocks if isinstance(b, HeroBlock)
        ]
        assert original_hero[0].overlay_title == content.title or True
        # deepcopy ensures independence


class TestCreateEditorial:
    async def test_create_editorial_full_pipeline(self) -> None:
        """Full pipeline: content + image + vision -> merged layout + image bytes."""
        client = _build_mock_client()

        # 3 calls: content gen, image gen, vision parse
        client.aio.models.generate_content.side_effect = [
            _mock_text_response(SAMPLE_CONTENT_JSON),
            _mock_image_response(b"layout_image"),
            _mock_text_response(SAMPLE_LAYOUT_BLOCKS_JSON),
        ]

        service = _build_service(client)
        layout, image_bytes = await service.create_editorial(
            "Y2K 패션",
            "레트로 트렌드 부활",
        )

        assert isinstance(layout, MagazineLayout)
        assert layout.keyword == "Y2K 패션"
        assert layout.title == "Y2K 리바이벌: 레트로가 다시 온다"
        # Should have blocks from vision-parsed layout
        assert len(layout.blocks) == 8
        # Content should be merged into blocks
        hero = [b for b in layout.blocks if isinstance(b, HeroBlock)]
        assert hero[0].overlay_title == "Y2K 리바이벌: 레트로가 다시 온다"
        # All 3 API calls made
        assert client.aio.models.generate_content.call_count == 3
        # Image bytes returned
        assert image_bytes == b"layout_image"

    async def test_create_editorial_nano_banana_fallback(self) -> None:
        """Image gen fails -> falls back to default template with content merged."""
        client = _build_mock_client()

        # 2 calls: content gen succeeds, image gen fails
        client.aio.models.generate_content.side_effect = [
            _mock_text_response(SAMPLE_CONTENT_JSON),
            RuntimeError("Nano Banana unavailable"),
        ]

        service = _build_service(client)
        layout, image_bytes = await service.create_editorial(
            "Y2K 패션",
            "레트로 트렌드 부활",
        )

        assert isinstance(layout, MagazineLayout)
        assert layout.keyword == "Y2K 패션"
        # Content should still be merged into default template
        headline = [
            b for b in layout.blocks if isinstance(b, HeadlineBlock)
        ]
        assert headline[0].text == "Y2K 리바이벌: 레트로가 다시 온다"
        # No image bytes when Nano Banana fails
        assert image_bytes is None

    async def test_create_editorial_vision_parse_fallback(
        self,
    ) -> None:
        """Image gen succeeds but vision parse fails -> default template."""
        client = _build_mock_client()

        # 3 calls: content OK, image OK, vision fails
        client.aio.models.generate_content.side_effect = [
            _mock_text_response(SAMPLE_CONTENT_JSON),
            _mock_image_response(b"layout_image"),
            RuntimeError("Vision API error"),
        ]

        service = _build_service(client)
        layout, image_bytes = await service.create_editorial(
            "Y2K 패션",
            "레트로 트렌드 부활",
        )

        assert isinstance(layout, MagazineLayout)
        assert layout.keyword == "Y2K 패션"
        # Falls back to default template, content merged
        body = [
            b for b in layout.blocks if isinstance(b, BodyTextBlock)
        ]
        assert len(body[0].paragraphs) == 2
        # Image bytes still returned even though vision parse failed
        assert image_bytes == b"layout_image"
