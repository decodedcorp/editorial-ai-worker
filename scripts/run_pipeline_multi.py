"""Multi-scenario pipeline v4: fetches real data from Supabase DB.

7 scenarios with ZERO image/solution overlap, all URLs from DB.
"""

import asyncio
import logging
import os
import time
import uuid
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv(".env.local")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# DB Data Fetcher
# ──────────────────────────────────────────────

def fetch_db_data():
    """Fetch posts, spots, solutions from Supabase and build artist -> posts index."""
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    sb = create_client(url, key)

    # Fetch solutions with titles
    solutions = (
        sb.table("solutions")
        .select("id,spot_id,title,thumbnail_url,original_url,metadata,description")
        .not_.is_("title", "null")
        .neq("title", "")
        .execute()
    )
    logger.info("Fetched %d solutions from DB", len(solutions.data))

    # Map spots -> post_id
    spot_ids = list({s["spot_id"] for s in solutions.data if s["spot_id"]})
    spots_map = {}
    for i in range(0, len(spot_ids), 200):
        batch = spot_ids[i : i + 200]
        spots = sb.table("spots").select("id,post_id").in_("id", batch).execute()
        for sp in spots.data:
            spots_map[sp["id"]] = sp["post_id"]

    # Map post_id -> post
    post_ids = list(set(spots_map.values()))
    posts_map = {}
    for i in range(0, len(post_ids), 200):
        batch = post_ids[i : i + 200]
        posts = (
            sb.table("posts")
            .select("id,artist_name,group_name,image_url")
            .in_("id", batch)
            .execute()
        )
        for p in posts.data:
            posts_map[p["id"]] = p

    # Group: post_id -> {post, solutions}
    post_solutions = defaultdict(lambda: {"post": None, "solutions": []})
    for s in solutions.data:
        post_id = spots_map.get(s["spot_id"])
        if not post_id:
            continue
        post = posts_map.get(post_id)
        if not post:
            continue
        post_solutions[post_id]["post"] = post
        post_solutions[post_id]["solutions"].append(s)

    # Group by artist
    artist_posts = defaultdict(list)
    for pid, data in post_solutions.items():
        p = data["post"]
        # Deduplicate solutions by title
        seen_titles = set()
        unique_sols = []
        for s in data["solutions"]:
            t = (s.get("title") or "").strip().lower()
            if t and t not in seen_titles:
                seen_titles.add(t)
                unique_sols.append(s)
        if len(unique_sols) >= 2:
            artist_posts[f"{p['artist_name']}_{p['group_name']}"].append(
                {"post": p, "solutions": unique_sols}
            )

    # Sort each artist's posts by solution count (richest first)
    for key in artist_posts:
        artist_posts[key].sort(key=lambda x: -len(x["solutions"]))

    return artist_posts


def pick_posts(artist_posts, artist_key, count, used_images):
    """Pick top N posts for an artist, skipping already-used images."""
    results = []
    for data in artist_posts.get(artist_key, []):
        img = data["post"]["image_url"]
        if img in used_images:
            continue
        used_images.add(img)

        # Build enriched_context entry
        ctx = {
            "artist_name": data["post"]["artist_name"],
            "group_name": data["post"]["group_name"],
            "image_url": img,
            "solutions": [
                {
                    "title": s["title"],
                    "thumbnail_url": s.get("thumbnail_url") or "",
                    "original_url": s.get("original_url") or "",
                    "metadata": s.get("metadata") or {},
                    "description": s.get("description") or "",
                }
                for s in data["solutions"][:5]  # max 5 solutions per post
            ],
        }
        results.append(ctx)
        if len(results) >= count:
            break
    return results


# ──────────────────────────────────────────────
# Scenario Definitions (editorial direction only)
# ──────────────────────────────────────────────

SCENARIO_CONFIGS = [
    {
        "label": "인물: 제니 x Chloé 소프트럭셔리",
        "seed_keyword": "제니 Chloé 소프트 럭셔리",
        "category": "fashion",
        "curated_topics": [
            {
                "keyword": "제니 Chloé 소프트 럭셔리",
                "trend_background": (
                    "BLACKPINK 제니는 Chloé의 글로벌 앰배서더로서 '소프트 럭셔리' 트렌드의 "
                    "중심에 서 있다. 리브드 니트 탱크탑, 캐시미어 아이템, 뉴트럴 톤 팔레트로 "
                    "구성된 그녀의 스타일은 '과시하지 않는 럭셔리'의 정수를 보여준다."
                ),
                "related_keywords": ["soft luxury", "quiet luxury", "Chloé ambassador", "effortless chic"],
            },
        ],
        "artists": [("jennie_BLACKPINK", 2)],
    },
    {
        "label": "브랜드: 리사 x STELLA McCARTNEY",
        "seed_keyword": "리사 STELLA McCARTNEY 지속가능 패션",
        "category": "fashion",
        "curated_topics": [
            {
                "keyword": "리사 STELLA McCARTNEY 지속가능 패션",
                "trend_background": (
                    "BLACKPINK 리사는 STELLA McCARTNEY와 BVLGARI를 중심으로 "
                    "지속가능한 하이패션의 아이콘으로 자리매김했다. "
                    "비건 레더, 재활용 소재 데님, 에코 프렌들리 주얼리를 자연스럽게 착용하며 "
                    "패션과 환경의식의 조화를 보여준다."
                ),
                "related_keywords": ["sustainable fashion", "BVLGARI", "Gallery Dept", "eco luxury"],
            },
        ],
        "artists": [("lisa_BLACKPINK", 3)],
    },
    {
        "label": "취향: 로제 x SAINT LAURENT 올드머니",
        "seed_keyword": "로제 SAINT LAURENT 올드머니",
        "category": "fashion",
        "curated_topics": [
            {
                "keyword": "로제 SAINT LAURENT 올드머니",
                "trend_background": (
                    "BLACKPINK 로제는 SAINT LAURENT과 TIFFANY & Co.를 축으로 "
                    "'올드머니' 트렌드의 K-POP 대표 아이콘이다. "
                    "캐시미어 스웨터에 THE ROW 데님, NY Yankees 캡을 매치하는 "
                    "절묘한 하이-로우 믹스가 특징이다."
                ),
                "related_keywords": ["old money aesthetic", "TIFFANY", "THE ROW", "high-low mix"],
            },
        ],
        "artists": [("rose_BLACKPINK", 3)],
    },
    {
        "label": "아이템: 지수 x Cartier 주얼리",
        "seed_keyword": "지수 Cartier DIOR 주얼리 스타일링",
        "category": "fashion",
        "curated_topics": [
            {
                "keyword": "지수 Cartier DIOR 주얼리 스타일링",
                "trend_background": (
                    "BLACKPINK 지수는 Cartier Trinity 컬렉션과 DIOR 백으로 "
                    "'주얼리가 완성하는 스타일'의 교과서를 쓰고 있다. "
                    "alo yoga 애슬레저에 Cartier 네크리스를 레이어링하거나, "
                    "LEMAIRE 크루아상 백과 코지한 루즈핏을 매치하는 센스가 돋보인다."
                ),
                "related_keywords": ["Cartier Trinity", "DIOR", "jewelry styling", "LEMAIRE"],
            },
        ],
        "artists": [("jisoo_BLACKPINK", 3)],
    },
    {
        "label": "스트릿: 다니엘 캐주얼 감성",
        "seed_keyword": "다니엘 뉴진스 캐주얼 스트릿",
        "category": "fashion",
        "curated_topics": [
            {
                "keyword": "다니엘 뉴진스 캐주얼 스트릿",
                "trend_background": (
                    "NewJeans 다니엘은 NIKE, BAPE, CELINE을 자유롭게 넘나드는 "
                    "10대 특유의 발랄한 스트릿 감성으로 사랑받고 있다. "
                    "새틴 봄버 재킷에 에어맥스, 플라워 캡과 캐릭터 마스코트까지 — "
                    "하이엔드와 플레이풀함의 경계를 자유롭게 오가는 그녀의 스타일이다."
                ),
                "related_keywords": ["Gen Z casual", "NIKE", "CELINE", "playful style"],
            },
        ],
        "artists": [("danielle_NewJeans", 3)],
    },
    {
        "label": "비교: 제니 vs 리사 스타일배틀",
        "seed_keyword": "제니 vs 리사 스타일 배틀",
        "category": "fashion",
        "curated_topics": [
            {
                "keyword": "제니 vs 리사 BLACKPINK 스타일 배틀",
                "trend_background": (
                    "BLACKPINK의 투톱 패션 아이콘, 제니와 리사. "
                    "제니는 파인주얼리와 Supreme 캡으로 '하이-스트릿 믹스'를, "
                    "리사는 자신의 브랜드 LLOUD와 Christian Louboutin으로 "
                    "'셀럽 앙트레프러너' 스타일을 보여준다."
                ),
                "related_keywords": ["style battle", "BLACKPINK fashion", "K-pop rivalry"],
            },
        ],
        "artists": [("jennie_BLACKPINK", 2), ("lisa_BLACKPINK", 2)],
    },
    {
        "label": "크로스오버: K-POP 공항패션",
        "seed_keyword": "K-POP 공항패션 크로스오버",
        "category": "fashion",
        "curated_topics": [
            {
                "keyword": "K-POP 공항패션 크로스오버",
                "trend_background": (
                    "K-POP 4세대 아이콘들의 공항패션은 그 자체로 하나의 패션쇼다. "
                    "제니의 DSQUARED2 모헤어 니트와 CHANEL 네크리스 레이어링, "
                    "리사의 LOEWE 롱슬리브와 LV 캡의 믹스매치, "
                    "지수의 R13 레오파드 셔츠와 courrèges 와이드 팬츠의 빈티지 무드까지."
                ),
                "related_keywords": ["airport fashion", "K-pop style", "travel outfit", "4th gen"],
            },
        ],
        "artists": [("jennie_BLACKPINK", 1), ("lisa_BLACKPINK", 1), ("jisoo_BLACKPINK", 1)],
    },
]


def build_scenarios(artist_posts):
    """Build scenario dicts with real DB data for enriched_contexts."""
    used_images = set()
    scenarios = []

    for config in SCENARIO_CONFIGS:
        enriched_contexts = []
        for artist_key, count in config["artists"]:
            contexts = pick_posts(artist_posts, artist_key, count, used_images)
            enriched_contexts.extend(contexts)

        # Log what we got
        total_sols = sum(len(c["solutions"]) for c in enriched_contexts)
        logger.info(
            "[%s] %d posts, %d solutions",
            config["label"],
            len(enriched_contexts),
            total_sols,
        )

        scenarios.append((
            config["label"],
            {
                "seed_keyword": config["seed_keyword"],
                "category": config["category"],
                "curated_topics": config["curated_topics"],
                "enriched_contexts": enriched_contexts,
            },
        ))

    return scenarios


# ──────────────────────────────────────────────
# Pipeline stubs
# ──────────────────────────────────────────────

async def make_stub_curation(topics):
    async def stub(state):
        return {"curated_topics": topics}
    return stub


async def stub_design_spec(state):
    return {}


async def make_stub_source(contexts):
    async def stub(state):
        return {"enriched_contexts": contexts}
    return stub


async def stub_review(state):
    return {
        "review_result": {
            "passed": True,
            "criteria": [{"criterion": "skip", "passed": True, "reason": "Review skipped", "severity": "minor"}],
            "summary": "Auto-passed for testing.",
            "suggestions": [],
        },
        "pipeline_status": "awaiting_approval",
    }


async def auto_approve_admin_gate(state):
    from editorial_ai.services.content_service import save_pending_content

    current_draft = state.get("current_draft") or {}
    curation_input = state.get("curation_input") or {}
    review_result = state.get("review_result") or {}
    title = current_draft.get("title", "")
    keyword = curation_input.get("seed_keyword", "")
    review_summary = review_result.get("summary", "")
    thread_id = state.get("thread_id") or keyword or "unknown"
    saved = await save_pending_content(
        thread_id=thread_id,
        layout_json=current_draft,
        title=title,
        keyword=keyword,
        review_summary=review_summary,
    )
    content_id = saved.get("id", "")
    print(f"  Content saved: id={content_id}, title={title[:60]}", flush=True)
    return {
        "admin_decision": "approved",
        "current_draft_id": content_id,
        "pipeline_status": "awaiting_approval",
    }


async def stub_publish(state):
    from editorial_ai.services.content_service import update_content_status

    content_id = state.get("current_draft_id")
    if content_id:
        await update_content_status(content_id, "published")
    return {"pipeline_status": "published"}


async def run_scenario(label, scenario):
    from editorial_ai.graph import build_graph

    curation_stub = await make_stub_curation(scenario["curated_topics"])
    source_stub = await make_stub_source(scenario["enriched_contexts"])

    graph = build_graph(
        node_overrides={
            "curation": curation_stub,
            "design_spec": stub_design_spec,
            "source": source_stub,
            "review": stub_review,
            "admin_gate": auto_approve_admin_gate,
            "publish": stub_publish,
        }
    )

    thread_id = str(uuid.uuid4())
    initial_state = {
        "thread_id": thread_id,
        "curation_input": {
            "seed_keyword": scenario["seed_keyword"],
            "category": scenario["category"],
        },
    }

    start = time.time()
    print(f"\n{'='*60}", flush=True)
    print(f">>> [{label}] seed: {scenario['seed_keyword']}", flush=True)
    print(f"{'='*60}", flush=True)

    try:
        result = await graph.ainvoke(initial_state)
        elapsed = time.time() - start
        draft = result.get("current_draft", {})
        blocks = draft.get("blocks", [])
        print(f"  Completed in {elapsed:.1f}s", flush=True)
        print(f"  Title: {draft.get('title', 'N/A')}", flush=True)
        print(f"  Blocks: {len(blocks)} — {', '.join(b.get('type','?') for b in blocks)}", flush=True)

        # Show product enrichment status
        for b in blocks:
            if b.get("type") == "product_showcase":
                for p in b.get("products", []):
                    has_img = "✓" if p.get("image_url") else "✗"
                    has_link = "✓" if p.get("link_url") else "✗"
                    print(f"    {has_img}img {has_link}link | {p.get('name','')[:40]}", flush=True)

        print(f"  Status: {result.get('pipeline_status')}", flush=True)
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"  FAILED in {elapsed:.1f}s: {e}", flush=True)
        return False


async def main():
    from editorial_ai.services.content_service import list_contents

    total_start = time.time()
    print(">>> Multi-scenario pipeline v4 (DB-sourced, zero overlap)", flush=True)

    # Fetch all data from DB
    print(">>> Fetching data from Supabase...", flush=True)
    artist_posts = fetch_db_data()
    for key, posts in sorted(artist_posts.items(), key=lambda x: -len(x[1])):
        total_sols = sum(len(d["solutions"]) for d in posts)
        print(f"  {key}: {len(posts)} posts, {total_sols} solutions", flush=True)

    # Build scenarios
    all_scenarios = build_scenarios(artist_posts)
    print(f"\n>>> Running {len(all_scenarios)} scenarios sequentially", flush=True)

    results = []
    for label, scenario in all_scenarios:
        ok = await run_scenario(label, scenario)
        results.append((label, ok))

    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}", flush=True)
    print(f">>> All done in {total_elapsed:.1f}s", flush=True)
    print(f"{'='*60}", flush=True)

    for label, ok in results:
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {label}", flush=True)

    items = await list_contents()
    print(f"\n>>> Total saved contents: {len(items)}", flush=True)
    for item in items:
        print(f"  [{item['status']}] {item['title'][:60]}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
