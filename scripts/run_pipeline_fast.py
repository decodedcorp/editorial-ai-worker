"""Fast pipeline test: skip curation/source, use DB-sourced hardcoded topics.

Skips: curation (Gemini grounding), design_spec, source (Supabase fetch)
Runs:  editorial -> enrich -> review -> admin_gate -> publish
"""

import asyncio
import logging
import time
import uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

# Hardcoded curated_topics from DB (NewJeans fashion)
CURATED_TOPICS = [
    {
        "keyword": "NewJeans 패션",
        "trend_background": (
            "NewJeans는 Y2K 레트로와 미니멀 시크를 결합한 독보적인 패션 아이콘으로 자리잡았다. "
            "멤버들의 스트릿 스타일은 Miu Miu, Louis Vuitton, Chanel 등 하이엔드 브랜드와 "
            "Our Legacy, Dion Lee 같은 컨템포러리 브랜드를 믹스매치하는 것이 특징이다. "
            "특히 Hanni의 캐주얼 시크, Minji의 클래식 무드, Haerin의 아방가르드 실루엣이 "
            "각각의 개성을 보여주며 Z세대 패션 트렌드를 주도하고 있다."
        ),
        "related_keywords": ["Y2K fashion", "street style", "Miu Miu", "Louis Vuitton"],
    },
    {
        "keyword": "NewJeans street style",
        "trend_background": (
            "NewJeans 멤버들의 공항패션과 일상 스트릿룩이 SNS에서 큰 화제를 모으고 있다. "
            "Hyein의 오버사이즈 실루엣, Danielle의 페미닌 레이어링이 팬들 사이에서 "
            "가장 많이 레퍼런스되는 스타일이다."
        ),
        "related_keywords": ["airport fashion", "K-pop style", "Gen Z fashion"],
    },
]

# Enriched contexts from DB — full product metadata per member
ENRICHED_CONTEXTS = [
    {
        "artist_name": "hyein",
        "group_name": "NewJeans",
        "image_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/newjeanscloset/2024-10-11_07-50-58/2024-10-11_07-50-58_UTC_2.jpg",
        "solutions": [
            {
                "title": "LOUIS VUITTON Nano Alma Monogram Canvas",
                "thumbnail_url": "https://prod-images.fashionphile.com/thumb/57294989028590e248af0cf483e6bf36/57a2a5a59684434ce50059a5a5124844.jpg",
                "metadata": {"brand": "Louis Vuitton", "category": "Handbags", "material": ["Monogram Canvas", "Natural Leather"], "origin": "France"},
                "description": "A miniature replica of the iconic Alma bag with heritage appeal and modern functionality.",
            },
            {
                "title": "LOUIS VUITTON Spring Street Bag Charm",
                "thumbnail_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/items/5b31f75d-0a6b-4965-b16f-29dde3fc863b/12968.jpg",
                "metadata": {"brand": "Louis Vuitton", "category": "Accessories"},
                "description": "Gold bag charm key holder",
            },
            {
                "title": "LOUIS VUITTON Neverfull Bandoulière Inside Out MM",
                "thumbnail_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/items/5b31f75d-0a6b-4965-b16f-29dde3fc863b/12964.jpg",
                "metadata": {"brand": "Louis Vuitton", "category": "Bags"},
                "description": "Brown monogram shoulder bag",
            },
        ],
    },
    {
        "artist_name": "hanni",
        "group_name": "NewJeans",
        "image_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/newjeanscloset/2024-07-08_03-35-51/2024-07-08_03-35-51_UTC_2.jpg",
        "solutions": [
            {
                "title": "BAPE Skull STA #2 M1 Sneakers",
                "thumbnail_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/items/8788f8e1-259f-4c3c-a162-df2d01ffc918/10326.jpg",
                "metadata": {"brand": "BAPE", "category": "Shoes"},
                "description": "Black and white star sneakers",
            },
            {
                "title": "BAPE Red Heart Camouflage Outfit",
                "thumbnail_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/items/8788f8e1-259f-4c3c-a162-df2d01ffc918/10325.jpg",
                "metadata": {"brand": "BAPE", "category": "Tops"},
                "description": "Red heart camouflage hoodie and matching shorts with white crop top",
            },
            {
                "title": "GUCCI Oval Frame Sunglasses",
                "thumbnail_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/items/8788f8e1-259f-4c3c-a162-df2d01ffc918/10327.jpg",
                "metadata": {"brand": "GUCCI", "category": "Eyewear"},
                "description": "Black oval frame sunglasses",
            },
        ],
    },
    {
        "artist_name": "hanni",
        "group_name": "NewJeans",
        "image_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/newjeanscloset/2024-02-25_12-39-52/2024-02-25_12-39-52_UTC_3.jpg",
        "solutions": [
            {
                "title": "Alpha Industries x BAPE Shark Full Zip Hoodie",
                "thumbnail_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/items/a69bb11c-de3a-4621-a166-05b2ebae5d07/2888.jpg",
                "metadata": {"brand": "BAPE x Alpha Industries", "category": "Tops"},
                "description": "Grey cotton collaboration hoodie",
            },
            {
                "title": "GUCCI Denim Pants with Gucci Label",
                "thumbnail_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/items/a69bb11c-de3a-4621-a166-05b2ebae5d07/2889.jpg",
                "metadata": {"brand": "GUCCI", "category": "Bottoms"},
                "description": "Blue denim pants with lasered double G",
            },
        ],
    },
    {
        "artist_name": "minji",
        "group_name": "NewJeans",
        "image_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/newjeanscloset/2024-04-23_09-28-01/2024-04-23_09-28-01_UTC_6.jpg",
        "solutions": [
            {
                "title": "CHANEL Pre-Collection Blouse",
                "thumbnail_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/items/6e18f0f0-7cf8-4186-8de4-02f95dad5716/2855.jpg",
                "metadata": {"brand": "CHANEL", "category": "Tops"},
                "description": "Black leather blouse from pre-collection",
            },
            {
                "title": "CHANEL Pre-Collection Bermuda Shorts",
                "thumbnail_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/items/6e18f0f0-7cf8-4186-8de4-02f95dad5716/2856.jpg",
                "metadata": {"brand": "CHANEL", "category": "Bottoms", "material": ["Pearly Lambskin"]},
                "description": "Black pearly lambskin bermuda shorts",
            },
            {
                "title": "CHANEL Clutch with Chain",
                "thumbnail_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/items/6e18f0f0-7cf8-4186-8de4-02f95dad5716/2857.jpg",
                "metadata": {"brand": "CHANEL", "category": "Bags", "material": ["Velvet Nylon", "Crumpled Calfskin"]},
                "description": "Black quilted clutch with chain and pearl details",
            },
        ],
    },
    {
        "artist_name": "minji",
        "group_name": "NewJeans",
        "image_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/newjeanscloset/2024-06-07_13-36-53/2024-06-07_13-36-53_UTC_4.jpg",
        "solutions": [
            {
                "title": "STONEHENGE N0135 Necklace",
                "thumbnail_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/items/b0003203-00e7-4af0-9d1a-a71c6424255b/1446.jpg",
                "metadata": {"brand": "STONEHENGE", "category": "Accessories"},
                "description": "Silver diamond necklace",
            },
            {
                "title": "PoshyFreckles Low Slit Linen Skirt (Herringbone)",
                "thumbnail_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/items/b0003203-00e7-4af0-9d1a-a71c6424255b/1447.jpg",
                "metadata": {"brand": "PoshyFreckles", "category": "Bottoms", "material": ["Linen"]},
                "description": "Beige herringbone linen midi skirt",
            },
        ],
    },
    {
        "artist_name": "haerin",
        "group_name": "NewJeans",
        "image_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/newjeanscloset/2024-05-26_19-20-13/2024-05-26_19-20-13_UTC_5.jpg",
        "solutions": [
            {
                "title": "muum Nest Backpack (Black)",
                "thumbnail_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/items/1777346b-76c5-444f-82f4-6485985ca72d/10536.jpg",
                "metadata": {"brand": "muum", "category": "Bags"},
                "description": "Black nylon backpack",
            },
            {
                "title": "Wave Mermaid Skirt (Grey)",
                "metadata": {"brand": "Heights Store", "category": "Bottoms"},
                "description": "Grey maxi mermaid skirt",
            },
        ],
    },
    {
        "artist_name": "haerin",
        "group_name": "NewJeans",
        "image_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/newjeanscloset/2024-10-05_04-24-47/2024-10-05_04-24-47_UTC_3.jpg",
        "solutions": [
            {
                "title": "OJOS Inner Strap Light Windbreaker (Grey)",
                "thumbnail_url": "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev/items/9de00a13-7b31-4fb8-95a6-43f7c46880ab/12939.jpg",
                "metadata": {"brand": "OJOS", "category": "Tops"},
                "description": "Grey hooded windbreaker jacket",
            },
        ],
    },
]


async def stub_curation(state):
    """Skip curation, return hardcoded topics."""
    return {"curated_topics": CURATED_TOPICS}


async def stub_design_spec(state):
    """Skip design spec generation."""
    return {}


async def stub_source(state):
    """Skip source fetch, return hardcoded enriched contexts."""
    return {"enriched_contexts": ENRICHED_CONTEXTS}


async def auto_approve_admin_gate(state):
    """Auto-approve and save locally."""
    from editorial_ai.services.content_service import save_pending_content

    current_draft = state.get("current_draft") or {}
    curation_input = state.get("curation_input") or {}
    review_result = state.get("review_result") or {}

    title = current_draft.get("title", "")
    keyword = curation_input.get("seed_keyword", "")
    review_summary = review_result.get("summary", "")
    thread_id = state.get("thread_id") or keyword or "unknown"

    layout_image_base64 = state.get("layout_image_base64")

    saved = await save_pending_content(
        thread_id=thread_id,
        layout_json=current_draft,
        title=title,
        keyword=keyword,
        review_summary=review_summary,
        layout_image_base64=layout_image_base64,
    )
    content_id = saved.get("id", "")
    print(f"\n>>> Content saved: id={content_id}, title={title}", flush=True)

    return {
        "admin_decision": "approved",
        "current_draft_id": content_id,
        "pipeline_status": "awaiting_approval",
    }


async def stub_publish(state):
    """Mark as published locally."""
    from editorial_ai.services.content_service import update_content_status

    content_id = state.get("current_draft_id")
    if content_id:
        await update_content_status(content_id, "published")
        print(f">>> Content published: id={content_id}", flush=True)
    return {"pipeline_status": "published"}


async def stub_review(state):
    """Skip LLM review, auto-pass."""
    return {
        "review_result": {
            "passed": True,
            "criteria": [{"criterion": "skip", "passed": True, "reason": "Review skipped (Gemini outage)", "severity": "minor"}],
            "summary": "Review skipped due to Gemini API outage. Auto-passed.",
            "suggestions": [],
        },
        "pipeline_status": "awaiting_approval",
    }


async def run_pipeline():
    from editorial_ai.graph import build_graph
    from editorial_ai.services.content_service import list_contents

    graph = build_graph(
        node_overrides={
            "curation": stub_curation,
            "design_spec": stub_design_spec,
            "source": stub_source,
            "review": stub_review,
            "admin_gate": auto_approve_admin_gate,
            "publish": stub_publish,
        }
    )

    thread_id = str(uuid.uuid4())
    initial_state = {
        "thread_id": thread_id,
        "curation_input": {
            "seed_keyword": "NewJeans 패션",
            "category": "fashion",
        },
    }

    start = time.time()
    print(f">>> thread_id: {thread_id}", flush=True)
    print('>>> Fast pipeline started: seed_keyword="NewJeans 패션"', flush=True)
    print(">>> Skipping: curation, design_spec, source (using DB hardcoded data)", flush=True)
    print()

    result = await graph.ainvoke(initial_state)

    elapsed = time.time() - start
    print(f"\n>>> Pipeline completed in {elapsed:.1f}s", flush=True)
    print(f"pipeline_status: {result.get('pipeline_status')}", flush=True)

    draft = result.get("current_draft", {})
    print(f"title: {draft.get('title', 'N/A')}", flush=True)
    blocks = draft.get("blocks", [])
    print(f"blocks: {len(blocks)}", flush=True)
    for b in blocks:
        print(f"  - {b.get('type', '?')}", flush=True)

    review = result.get("review_result", {})
    print(f"review passed: {review.get('passed')}", flush=True)
    print(f"revision_count: {result.get('revision_count', 0)}", flush=True)

    items = await list_contents()
    print(f"\n>>> Saved contents: {len(items)}", flush=True)
    for item in items:
        print(
            f"  id={item['id']}, status={item['status']}, title={item['title'][:50]}",
            flush=True,
        )

    # Auto-open layout image if generated
    layout_image_b64 = result.get("layout_image_base64")
    if layout_image_b64:
        import base64
        import subprocess
        from pathlib import Path

        img_dir = Path("data/layout_images")
        img_dir.mkdir(parents=True, exist_ok=True)
        img_path = img_dir / "latest.png"
        img_path.write_bytes(base64.b64decode(layout_image_b64))
        print(f"\n>>> Layout image saved: {img_path}", flush=True)
        # Auto-open on macOS
        subprocess.Popen(["open", str(img_path)])
    else:
        print("\n>>> No layout image generated (Nano Banana skipped or failed)", flush=True)


if __name__ == "__main__":
    asyncio.run(run_pipeline())
