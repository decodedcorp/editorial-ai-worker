"""Tests for enrich_from_posts node and _enrich_products_from_solutions.

Verifies link_url/image_url injection from solution data (v5 bug fix).
No real API/DB calls — pure unit tests.
"""

from __future__ import annotations

from editorial_ai.models.layout import (
    MagazineLayout,
    ProductItem,
    ProductShowcaseBlock,
    HeroBlock,
    HeadlineBlock,
)
from editorial_ai.nodes.enrich_from_posts import (
    enrich_from_posts_node,
    _inject_posts_data,
    _collect_products,
)
from editorial_ai.services.editorial_service import EditorialService


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

def _sample_enriched_contexts():
    return [
        {
            "artist_name": "제니",
            "group_name": "BLACKPINK",
            "image_url": "https://example.com/jennie.jpg",
            "solutions": [
                {
                    "title": "CHANEL Silk Scarf",
                    "thumbnail_url": "https://thumb.example.com/chanel.jpg",
                    "original_url": "https://www.chanel.com/scarf",
                    "metadata": {"keywords": ["CHANEL"]},
                    "description": "Silk scarf by CHANEL",
                },
                {
                    "title": "Miu Miu Low Rise Denim",
                    "thumbnail_url": "https://thumb.example.com/miumiu.jpg",
                    "original_url": "https://www.miumiu.com/denim",
                    "metadata": {"keywords": ["Miu Miu"]},
                    "description": "Low rise denim",
                },
            ],
        },
    ]


def _sample_layout_with_products(product_names: list[str] | None = None):
    if product_names is None:
        product_names = ["CHANEL Silk Scarf", "Miu Miu Low Rise Denim"]
    return MagazineLayout(
        keyword="test",
        title="Test Layout",
        blocks=[
            HeroBlock(image_url=""),
            HeadlineBlock(text="Test"),
            ProductShowcaseBlock(
                products=[ProductItem(name=n) for n in product_names]
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Tests: _collect_products
# ---------------------------------------------------------------------------


class TestCollectProducts:
    def test_collects_original_url(self) -> None:
        """v5: _collect_products includes original_url from solution data."""
        products = _collect_products(_sample_enriched_contexts())
        assert len(products) >= 1
        for p in products:
            assert "original_url" in p
        chanel = next(p for p in products if "CHANEL" in p["name"])
        assert chanel["original_url"] == "https://www.chanel.com/scarf"
        assert chanel["thumbnail_url"] == "https://thumb.example.com/chanel.jpg"


# ---------------------------------------------------------------------------
# Tests: _inject_posts_data (link_url injection)
# ---------------------------------------------------------------------------


class TestInjectPostsData:
    def test_injects_link_url(self) -> None:
        """v5: _inject_posts_data sets link_url from original_url."""
        layout = _sample_layout_with_products()
        result = _inject_posts_data(layout, _sample_enriched_contexts())

        for block in result.blocks:
            if isinstance(block, ProductShowcaseBlock):
                for p in block.products:
                    assert p.link_url is not None, f"link_url missing for {p.name}"
                    assert p.link_url.startswith("https://")
                    assert p.image_url is not None, f"image_url missing for {p.name}"

    def test_no_enriched_contexts_returns_as_is(self) -> None:
        """Empty contexts should not crash."""
        layout = _sample_layout_with_products()
        result = _inject_posts_data(layout, [])
        for block in result.blocks:
            if isinstance(block, ProductShowcaseBlock):
                for p in block.products:
                    assert p.link_url is None


# ---------------------------------------------------------------------------
# Tests: EditorialService._enrich_products_from_solutions
# ---------------------------------------------------------------------------


class TestEnrichProductsFromSolutions:
    def test_exact_name_match(self) -> None:
        """Products matched by exact name get link_url and image_url."""
        layout = _sample_layout_with_products(["CHANEL Silk Scarf"])
        EditorialService._enrich_products_from_solutions(
            layout, _sample_enriched_contexts()
        )
        block = [b for b in layout.blocks if isinstance(b, ProductShowcaseBlock)][0]
        assert block.products[0].link_url == "https://www.chanel.com/scarf"
        assert block.products[0].image_url == "https://thumb.example.com/chanel.jpg"

    def test_substring_match(self) -> None:
        """Products matched by substring get enriched."""
        layout = _sample_layout_with_products(["Silk Scarf"])
        EditorialService._enrich_products_from_solutions(
            layout, _sample_enriched_contexts()
        )
        block = [b for b in layout.blocks if isinstance(b, ProductShowcaseBlock)][0]
        assert block.products[0].link_url == "https://www.chanel.com/scarf"

    def test_unmatched_gets_remaining_solution(self) -> None:
        """Unmatched products get remaining solutions in order (pass 2)."""
        layout = _sample_layout_with_products(["Unknown Product XYZ"])
        EditorialService._enrich_products_from_solutions(
            layout, _sample_enriched_contexts()
        )
        block = [b for b in layout.blocks if isinstance(b, ProductShowcaseBlock)][0]
        # Should get first available solution
        assert block.products[0].link_url is not None
        assert block.products[0].image_url is not None


# ---------------------------------------------------------------------------
# Tests: enrich_from_posts_node (integration)
# ---------------------------------------------------------------------------


class TestEnrichFromPostsNode:
    async def test_no_draft_returns_error(self) -> None:
        """Missing current_draft returns error_log."""
        result = await enrich_from_posts_node({
            "current_draft": None,
            "enriched_contexts": _sample_enriched_contexts(),
        })
        assert "error_log" in result

    async def test_no_contexts_skips(self) -> None:
        """Empty enriched_contexts returns empty dict (no-op)."""
        layout = _sample_layout_with_products()
        result = await enrich_from_posts_node({
            "current_draft": layout.model_dump(),
            "enriched_contexts": [],
        })
        assert result == {}

    async def test_full_enrichment(self) -> None:
        """Full node execution injects link_url into products."""
        layout = _sample_layout_with_products()
        result = await enrich_from_posts_node({
            "current_draft": layout.model_dump(),
            "enriched_contexts": _sample_enriched_contexts(),
        })
        assert "current_draft" in result
        draft = result["current_draft"]
        for b in draft["blocks"]:
            if b["type"] == "product_showcase":
                for p in b["products"]:
                    assert p["link_url"] is not None, f"link_url missing: {p['name']}"
