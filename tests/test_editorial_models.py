"""Tests for editorial and layout Pydantic models."""

import pytest
from pydantic import ValidationError

from editorial_ai.models.editorial import EditorialContent, ProductMention, CelebMention
from editorial_ai.models.layout import (
    BodyTextBlock,
    CelebFeatureBlock,
    CelebItem,
    CreditEntry,
    CreditsBlock,
    DividerBlock,
    HashtagBarBlock,
    HeadlineBlock,
    HeroBlock,
    ImageGalleryBlock,
    ImageItem,
    KeyValuePair,
    MagazineLayout,
    ProductItem,
    ProductShowcaseBlock,
    PullQuoteBlock,
    create_default_template,
)


class TestMagazineLayoutRoundtrip:
    """Test 1: MagazineLayout with multiple block types round-trips through JSON."""

    def test_magazine_layout_valid_roundtrip(self) -> None:
        layout = MagazineLayout(
            title="Summer 2026 Trends",
            keyword="summer fashion",
            subtitle="The hottest looks",
            blocks=[
                HeroBlock(image_url="https://example.com/hero.jpg", overlay_title="Summer"),
                HeadlineBlock(text="Summer 2026 Trends", level=1),
                BodyTextBlock(paragraphs=["First paragraph.", "Second paragraph."]),
                ImageGalleryBlock(
                    images=[ImageItem(url="https://example.com/img1.jpg", alt="Look 1")],
                    layout_style="carousel",
                ),
                PullQuoteBlock(quote="Fashion is art.", attribution="Anna Wintour"),
                ProductShowcaseBlock(
                    products=[ProductItem(name="Silk Dress", brand="Gucci", description="A flowing silk dress.")]
                ),
                CelebFeatureBlock(
                    celebs=[CelebItem(name="Jisoo", description="K-pop icon and fashion ambassador.")]
                ),
                DividerBlock(style="ornament"),
                HashtagBarBlock(hashtags=["#summer2026", "#fashion"]),
                CreditsBlock(entries=[CreditEntry(role="Editor", name="AI")]),
            ],
            metadata=[KeyValuePair(key="source", value="curation")],
        )

        json_str = layout.model_dump_json()
        restored = MagazineLayout.model_validate_json(json_str)

        assert restored.title == layout.title
        assert restored.keyword == layout.keyword
        assert restored.schema_version == "1.0"
        assert len(restored.blocks) == 10
        assert restored.metadata[0].key == "source"


class TestBlockDiscriminator:
    """Test 2: Mixed blocks serialize/deserialize with correct type discriminators."""

    def test_block_discriminator_works(self) -> None:
        layout = MagazineLayout(
            title="Test",
            keyword="test",
            blocks=[
                HeroBlock(image_url=""),
                BodyTextBlock(paragraphs=["text"]),
                DividerBlock(),
            ],
        )

        json_str = layout.model_dump_json()
        restored = MagazineLayout.model_validate_json(json_str)

        assert restored.blocks[0].type == "hero"
        assert restored.blocks[1].type == "body_text"
        assert restored.blocks[2].type == "divider"


class TestDefaultTemplate:
    """Tests 3 & 4: Default template structure and schema version."""

    def test_default_template_structure(self) -> None:
        template = create_default_template("streetwear", "Streetwear Guide")

        block_types = [b.type for b in template.blocks]
        assert "hero" in block_types
        assert "headline" in block_types
        assert "body_text" in block_types
        assert "product_showcase" in block_types
        assert "celeb_feature" in block_types
        assert "hashtag_bar" in block_types
        assert "credits" in block_types
        assert template.keyword == "streetwear"
        assert template.title == "Streetwear Guide"

    def test_default_template_has_schema_version(self) -> None:
        template = create_default_template("test", "Test")
        assert template.schema_version == "1.0"


class TestEditorialContent:
    """Tests 5 & 6: EditorialContent validation."""

    def test_editorial_content_valid(self) -> None:
        content = EditorialContent(
            keyword="denim",
            title="Denim Revival",
            subtitle="Back to basics",
            body_paragraphs=["Denim is timeless.", "This season it returns."],
            pull_quotes=["Denim never dies."],
            product_mentions=[ProductMention(name="501 Jeans", brand="Levi's", context="classic fit")],
            celeb_mentions=[CelebMention(name="Hailey Bieber", context="spotted wearing vintage denim")],
            hashtags=["#denim", "#revival"],
            credits=[CreditEntry(role="Writer", name="AI")],
        )

        json_str = content.model_dump_json()
        restored = EditorialContent.model_validate_json(json_str)

        assert restored.keyword == "denim"
        assert restored.title == "Denim Revival"
        assert len(restored.body_paragraphs) == 2
        assert len(restored.product_mentions) == 1
        assert len(restored.celeb_mentions) == 1

    def test_editorial_content_minimal(self) -> None:
        content = EditorialContent(
            keyword="minimal",
            title="Minimal Test",
            body_paragraphs=["One paragraph."],
        )

        assert content.subtitle is None
        assert content.pull_quotes == []
        assert content.product_mentions == []
        assert content.celeb_mentions == []
        assert content.hashtags == []
        assert content.credits == []


class TestLayoutValidation:
    """Tests 7 & 8: Validation error handling."""

    def test_layout_rejects_invalid_block_type(self) -> None:
        with pytest.raises(ValidationError):
            MagazineLayout.model_validate(
                {
                    "title": "Bad",
                    "keyword": "bad",
                    "blocks": [{"type": "nonexistent_block"}],
                }
            )

    def test_headline_level_range(self) -> None:
        # Valid range
        HeadlineBlock(text="OK", level=1)
        HeadlineBlock(text="OK", level=3)

        # Below range
        with pytest.raises(ValidationError):
            HeadlineBlock(text="Bad", level=0)

        # Above range
        with pytest.raises(ValidationError):
            HeadlineBlock(text="Bad", level=4)
