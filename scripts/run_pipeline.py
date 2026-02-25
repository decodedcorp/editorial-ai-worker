"""Run the editorial pipeline with posts data source (no DB writes).

Usage:
    python -m scripts.run_pipeline
    python -m scripts.run_pipeline --keyword "NewJeans fashion"
    python -m scripts.run_pipeline --keyword "jennie street style" --skip-curation

Runs: curation → source → editorial → enrich → review (skips admin_gate/publish)
Results are printed to stdout as JSON.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from editorial_ai.graph import build_graph
from editorial_ai.nodes.enrich_from_posts import enrich_from_posts_node
from editorial_ai.nodes.source import source_node
from editorial_ai.nodes.stubs import stub_admin_gate, stub_publish

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def build_test_graph(*, skip_curation: bool = False):
    """Build graph with posts-based source/enrich and stubbed admin/publish."""
    overrides = {
        "source": source_node,
        "enrich": enrich_from_posts_node,
        "admin_gate": stub_admin_gate,
        "publish": stub_publish,
    }
    if skip_curation:
        # Passthrough: preserve curated_topics already in state
        overrides["curation"] = lambda state: {"pipeline_status": "sourcing"}
    return build_graph(node_overrides=overrides)


async def run(keyword: str, *, skip_curation: bool = False):
    """Execute the pipeline and print results."""
    graph = build_test_graph(skip_curation=skip_curation)

    initial_state = {
        "curation_input": {"keyword": keyword, "seed_keyword": keyword},
        "curated_topics": [],
        "enriched_contexts": [],
        "current_draft": None,
        "current_draft_id": None,
        "tool_calls_log": [],
        "review_result": None,
        "revision_count": 0,
        "feedback_history": [],
        "thread_id": None,
        "admin_decision": None,
        "admin_feedback": None,
        "pipeline_status": "curating",
        "error_log": [],
    }

    if skip_curation:
        # Skip AI curation, use keyword directly as curated topic
        initial_state["curated_topics"] = [
            {
                "keyword": keyword,
                "trend_background": f"'{keyword}' 관련 최신 패션 트렌드",
                "related_keywords": [keyword],
            }
        ]

    logger.info("Starting pipeline with keyword: %s (skip_curation=%s)", keyword, skip_curation)

    result = await graph.ainvoke(initial_state)

    # Print summary
    print("\n" + "=" * 60)
    print("PIPELINE RESULT")
    print("=" * 60)

    status = result.get("pipeline_status", "unknown")
    print(f"Status: {status}")

    errors = result.get("error_log", [])
    if errors:
        print(f"Errors: {errors}")

    # Curated topics
    topics = result.get("curated_topics", [])
    print(f"\nCurated Topics ({len(topics)}):")
    for t in topics[:3]:
        print(f"  - {t.get('keyword', 'N/A')}")

    # Enriched contexts (posts data)
    contexts = result.get("enriched_contexts", [])
    print(f"\nSourced Posts ({len(contexts)}):")
    for ctx in contexts[:5]:
        artist = ctx.get("artist_name", "?")
        sols = ctx.get("solutions", [])
        print(f"  - {artist}: {len(sols)} solutions")

    # Review result
    review = result.get("review_result")
    if review:
        print(f"\nReview: {'PASSED' if review.get('passed') else 'FAILED'}")
        print(f"  Summary: {review.get('summary', 'N/A')}")

    # Current draft (MagazineLayout)
    draft = result.get("current_draft")
    if draft:
        print(f"\nMagazine Layout:")
        print(f"  Title: {draft.get('title', 'N/A')}")
        print(f"  Keyword: {draft.get('keyword', 'N/A')}")
        blocks = draft.get("blocks", [])
        print(f"  Blocks ({len(blocks)}):")
        for b in blocks:
            btype = b.get("type", "?")
            detail = ""
            if btype == "hero":
                url = b.get("image_url", "")
                detail = f" → {url[:80]}..." if url else " → (empty)"
            elif btype == "body_text":
                paras = b.get("paragraphs", [])
                detail = f" → {len(paras)} paragraphs"
            elif btype == "product_showcase":
                prods = b.get("products", [])
                detail = f" → {len(prods)} products"
                for p in prods[:2]:
                    detail += f"\n      - {p.get('name', '?')}"
            elif btype == "celeb_feature":
                celebs = b.get("celebs", [])
                detail = f" → {len(celebs)} celebs"
                for c in celebs[:2]:
                    detail += f"\n      - {c.get('name', '?')}"
            elif btype == "hashtag_bar":
                tags = b.get("hashtags", [])
                detail = f" → {tags}"
            print(f"    [{btype}]{detail}")

        # Save full JSON
        output_path = Path(__file__).parent / "output_layout.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(draft, f, ensure_ascii=False, indent=2)
        print(f"\n  Full layout JSON saved to: {output_path}")
    else:
        print("\nNo draft generated.")


def main():
    parser = argparse.ArgumentParser(description="Run editorial pipeline with posts data")
    parser.add_argument("--keyword", default="NewJeans fashion", help="Seed keyword")
    parser.add_argument("--skip-curation", action="store_true", help="Skip AI curation, use keyword directly")
    args = parser.parse_args()

    asyncio.run(run(args.keyword, skip_curation=args.skip_curation))


if __name__ == "__main__":
    main()
