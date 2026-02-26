"""Run editorial pipeline end-to-end with local content storage.

admin_gate: saves to local JSON + auto-approves (no interrupt, no checkpointer needed)
publish: stub (no Supabase write)
"""

import asyncio
import logging
import time
import uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


async def auto_approve_admin_gate(state):
    """Admin gate that saves content locally and auto-approves (no interrupt)."""
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
    print(f"\n>>> Content saved: id={content_id}, title={title}", flush=True)

    return {
        "admin_decision": "approved",
        "current_draft_id": content_id,
        "pipeline_status": "awaiting_approval",
    }


async def stub_publish(state):
    """Mark content as published (no Supabase write)."""
    from editorial_ai.services.content_service import update_content_status

    content_id = state.get("current_draft_id")
    if content_id:
        await update_content_status(content_id, "published")
        print(f">>> Content published: id={content_id}", flush=True)
    return {"pipeline_status": "published"}


async def run_pipeline():
    from editorial_ai.graph import build_graph
    from editorial_ai.services.content_service import list_contents

    graph = build_graph(
        node_overrides={
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
    print('>>> Pipeline started: seed_keyword="NewJeans 패션"', flush=True)
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

    items = await list_contents()
    print(f"\n>>> Saved contents: {len(items)}", flush=True)
    for item in items:
        print(
            f"  id={item['id']}, status={item['status']}, title={item['title'][:50]}",
            flush=True,
        )


if __name__ == "__main__":
    asyncio.run(run_pipeline())
