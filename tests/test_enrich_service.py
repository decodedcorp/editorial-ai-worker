"""Unit tests for enrich_service with mocked Gemini + Supabase dependencies."""

import json
from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from editorial_ai.models.celeb import Celeb
from editorial_ai.models.editorial import CelebMention, EditorialContent, ProductMention
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
)
from editorial_ai.models.product import Product
from editorial_ai.services.enrich_service import (
    enrich_editorial_content,
    expand_keywords,
    extract_celeb_names,
    extract_product_names,
    rebuild_layout_with_db_data,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CELEB_DB = Celeb(
    id="celeb-123",
    name="제니",
    name_en="Jennie",
    category="idol",
    profile_image_url="https://example.com/jennie.jpg",
    description="BLACKPINK member and fashion icon",
)

SAMPLE_PRODUCT_DB = Product(
    id="prod-456",
    name="클래식 플랩 백",
    brand="Chanel",
    category="bags",
    price=7500000,
    image_url="https://example.com/chanel-flap.jpg",
    description="Iconic Chanel classic flap bag",
)

SAMPLE_LAYOUT = MagazineLayout(
    keyword="Y2K",
    title="Y2K 트렌드의 귀환",
    blocks=[
        HeroBlock(image_url="", overlay_title="Y2K 트렌드의 귀환"),
        HeadlineBlock(text="Y2K 트렌드의 귀환"),
        BodyTextBlock(paragraphs=["Y2K 패션이 다시 돌아왔다.", "레트로 감성이 MZ세대를 사로잡고 있다."]),
        CelebFeatureBlock(
            celebs=[CelebItem(name="제니", description="Y2K 스타일 아이콘")]
        ),
        ProductShowcaseBlock(
            products=[ProductItem(name="클래식 플랩 백", brand="Chanel", description="Y2K 감성 백")]
        ),
        HashtagBarBlock(hashtags=["Y2K", "레트로"]),
        CreditsBlock(entries=[CreditEntry(role="AI Editor", name="decoded editorial")]),
    ],
)

SAMPLE_EDITORIAL_CONTENT = EditorialContent(
    keyword="Y2K",
    title="Y2K 트렌드의 귀환",
    subtitle="2000년대 감성의 재해석",
    body_paragraphs=["제니가 이끄는 Y2K 트렌드.", "Chanel 클래식 플랩 백이 다시 주목받고 있다."],
    pull_quotes=["Y2K는 단순한 복고가 아니다"],
    celeb_mentions=[CelebMention(name="제니", context="BLACKPINK 멤버이자 패션 아이콘")],
    product_mentions=[ProductMention(name="클래식 플랩 백", brand="Chanel", context="아이코닉한 Y2K 감성 백")],
    hashtags=["Y2K", "레트로", "제니"],
)


def _mock_gemini_response(text: str) -> MagicMock:
    """Create a mock Gemini response with .text attribute."""
    resp = MagicMock()
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# Extract tests
# ---------------------------------------------------------------------------


def test_extract_celeb_names() -> None:
    names = extract_celeb_names(SAMPLE_LAYOUT)
    assert names == ["제니"]


def test_extract_product_names() -> None:
    names = extract_product_names(SAMPLE_LAYOUT)
    assert names == ["클래식 플랩 백"]


def test_extract_celeb_names_no_blocks() -> None:
    layout = MagazineLayout(
        keyword="test",
        title="test",
        blocks=[HeroBlock(image_url=""), BodyTextBlock(paragraphs=["hello"])],
    )
    names = extract_celeb_names(layout)
    assert names == []


# ---------------------------------------------------------------------------
# Keyword expansion tests
# ---------------------------------------------------------------------------


async def test_expand_keywords_success() -> None:
    mock_client = MagicMock()
    expected_terms = ["레트로", "빈티지", "로우라이즈", "크롭탑"]
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=_mock_gemini_response(json.dumps(expected_terms, ensure_ascii=False))
    )

    result = await expand_keywords(mock_client, "Y2K")
    assert result == expected_terms


async def test_expand_keywords_parse_error() -> None:
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=_mock_gemini_response("this is not json at all!!!")
    )

    result = await expand_keywords(mock_client, "Y2K")
    assert result == []


# ---------------------------------------------------------------------------
# Layout rebuild tests
# ---------------------------------------------------------------------------


def test_rebuild_layout_with_db_data() -> None:
    layout = deepcopy(SAMPLE_LAYOUT)
    enriched = rebuild_layout_with_db_data(
        layout, SAMPLE_EDITORIAL_CONTENT, [SAMPLE_CELEB_DB], [SAMPLE_PRODUCT_DB]
    )

    # Check celeb_id populated
    celeb_block = [b for b in enriched.blocks if isinstance(b, CelebFeatureBlock)][0]
    assert len(celeb_block.celebs) == 1
    assert celeb_block.celebs[0].celeb_id == "celeb-123"
    assert celeb_block.celebs[0].name == "제니"
    assert celeb_block.celebs[0].image_url == "https://example.com/jennie.jpg"

    # Check product_id populated
    product_block = [b for b in enriched.blocks if isinstance(b, ProductShowcaseBlock)][0]
    assert len(product_block.products) == 1
    assert product_block.products[0].product_id == "prod-456"
    assert product_block.products[0].name == "클래식 플랩 백"
    assert product_block.products[0].brand == "Chanel"
    assert product_block.products[0].image_url == "https://example.com/chanel-flap.jpg"

    # Check body_paragraphs updated
    body_block = [b for b in enriched.blocks if isinstance(b, BodyTextBlock)][0]
    assert body_block.paragraphs == SAMPLE_EDITORIAL_CONTENT.body_paragraphs


def test_rebuild_layout_preserves_input() -> None:
    original_layout = deepcopy(SAMPLE_LAYOUT)
    original_blocks_count = len(original_layout.blocks)

    # Get original celeb block state
    original_celeb_block = [b for b in original_layout.blocks if isinstance(b, CelebFeatureBlock)][0]
    original_celeb_id = original_celeb_block.celebs[0].celeb_id  # Should be None

    rebuild_layout_with_db_data(
        original_layout, SAMPLE_EDITORIAL_CONTENT, [SAMPLE_CELEB_DB], [SAMPLE_PRODUCT_DB]
    )

    # Original layout must NOT be mutated
    assert len(original_layout.blocks) == original_blocks_count
    celeb_block = [b for b in original_layout.blocks if isinstance(b, CelebFeatureBlock)][0]
    assert celeb_block.celebs[0].celeb_id == original_celeb_id  # Still None


# ---------------------------------------------------------------------------
# Full orchestration tests
# ---------------------------------------------------------------------------


@patch("editorial_ai.services.enrich_service.search_products_multi", new_callable=AsyncMock)
@patch("editorial_ai.services.enrich_service.search_celebs_multi", new_callable=AsyncMock)
@patch("editorial_ai.services.enrich_service.get_genai_client")
async def test_enrich_editorial_content_no_db_results(
    mock_get_client: MagicMock,
    mock_search_celebs: AsyncMock,
    mock_search_products: AsyncMock,
) -> None:
    # Setup: Gemini returns keywords but DB returns nothing
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=_mock_gemini_response('["레트로", "빈티지"]')
    )
    mock_get_client.return_value = mock_client
    mock_search_celebs.return_value = []
    mock_search_products.return_value = []

    layout = deepcopy(SAMPLE_LAYOUT)
    result = await enrich_editorial_content(layout)

    # Should return original layout unchanged
    assert result is layout
    assert result.keyword == "Y2K"


@patch("editorial_ai.services.enrich_service.search_products_multi", new_callable=AsyncMock)
@patch("editorial_ai.services.enrich_service.search_celebs_multi", new_callable=AsyncMock)
@patch("editorial_ai.services.enrich_service.get_genai_client")
async def test_enrich_editorial_content_success(
    mock_get_client: MagicMock,
    mock_search_celebs: AsyncMock,
    mock_search_products: AsyncMock,
) -> None:
    # Setup mock Gemini client
    mock_client = MagicMock()
    enriched_json = SAMPLE_EDITORIAL_CONTENT.model_dump_json()

    # First call: keyword expansion, Second call: re-generation
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=[
            _mock_gemini_response('["레트로", "빈티지"]'),  # keyword expansion
            _mock_gemini_response(enriched_json),  # re-generation
        ]
    )
    mock_get_client.return_value = mock_client

    # DB returns celebs and products
    mock_search_celebs.return_value = [SAMPLE_CELEB_DB]
    mock_search_products.return_value = [SAMPLE_PRODUCT_DB]

    layout = deepcopy(SAMPLE_LAYOUT)
    result = await enrich_editorial_content(layout)

    # Should return enriched layout with DB IDs
    assert result is not layout  # New object (deepcopy)
    celeb_block = [b for b in result.blocks if isinstance(b, CelebFeatureBlock)][0]
    assert celeb_block.celebs[0].celeb_id == "celeb-123"

    product_block = [b for b in result.blocks if isinstance(b, ProductShowcaseBlock)][0]
    assert product_block.products[0].product_id == "prod-456"

    # Body paragraphs should be from enriched content
    body_block = [b for b in result.blocks if isinstance(b, BodyTextBlock)][0]
    assert body_block.paragraphs == SAMPLE_EDITORIAL_CONTENT.body_paragraphs

    # Verify search was called with mention names + expanded keywords
    celeb_search_args = mock_search_celebs.call_args[0][0]
    assert "제니" in celeb_search_args
    assert "레트로" in celeb_search_args
