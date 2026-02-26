---
phase: quick-002
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/editorial_ai/api/schemas.py
  - src/editorial_ai/api/routes/pipeline.py
  - src/editorial_ai/nodes/curation.py
  - src/editorial_ai/nodes/source.py
  - admin/src/lib/types.ts
  - admin/src/components/new-content-modal.tsx
autonomous: true

must_haves:
  truths:
    - "User can select 'AI DB Search' mode in the new content modal"
    - "User enters only a keyword, AI expands it into DB search terms"
    - "Pipeline searches DB (posts, celebs, products) using AI-expanded keywords"
    - "Found DB sources flow into editorial generation as enriched_contexts"
    - "No Google Search grounding is used - only internal DB search"
  artifacts:
    - path: "src/editorial_ai/nodes/curation.py"
      provides: "ai_db_search mode handler that uses LLM to expand keyword into search terms"
      contains: "ai_db_search"
    - path: "src/editorial_ai/api/schemas.py"
      provides: "TriggerRequest.mode accepts ai_db_search"
      contains: "ai_db_search"
    - path: "admin/src/components/new-content-modal.tsx"
      provides: "Third mode tab for AI DB Search"
      contains: "ai_db_search"
  key_links:
    - from: "admin/src/components/new-content-modal.tsx"
      to: "src/editorial_ai/api/routes/pipeline.py"
      via: "POST /api/pipeline/trigger with mode=ai_db_search"
      pattern: "ai_db_search"
    - from: "src/editorial_ai/nodes/curation.py"
      to: "src/editorial_ai/nodes/source.py"
      via: "curated_topics with expanded search keywords"
      pattern: "curated_topics"
---

<objective>
Add a new `ai_db_search` pipeline mode where the user enters only a keyword, AI expands it into optimized DB search terms (celeb names, brand names, categories), and the source_node searches the internal DB using those terms -- no external Google Search grounding.

Purpose: Enable keyword-only content creation that leverages the existing DB without requiring manual source selection (db_source) or expensive external trend analysis (ai_curation).

Output: Working end-to-end `ai_db_search` mode from admin UI through pipeline execution.
</objective>

<execution_context>
@/Users/kiyeol/.claude-pers/get-shit-done/workflows/execute-plan.md
@/Users/kiyeol/.claude-pers/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/editorial_ai/api/schemas.py
@src/editorial_ai/api/routes/pipeline.py
@src/editorial_ai/nodes/curation.py
@src/editorial_ai/nodes/source.py
@src/editorial_ai/services/curation_service.py
@src/editorial_ai/models/curation.py
@admin/src/components/new-content-modal.tsx
@admin/src/lib/types.ts
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend - Add ai_db_search mode to curation_node and pipeline trigger</name>
  <files>
    src/editorial_ai/api/schemas.py
    src/editorial_ai/api/routes/pipeline.py
    src/editorial_ai/nodes/curation.py
  </files>
  <action>
    **1. schemas.py** - Update TriggerRequest.mode comment to include "ai_db_search":
    ```python
    mode: str = "ai_curation"  # "ai_curation" | "db_source" | "ai_db_search"
    ```

    **2. curation_node in curation.py** - Add `ai_db_search` mode handler BEFORE the existing ai_curation logic. When mode == "ai_db_search":
    - Use Gemini (same client/model as existing CurationService) to expand the seed_keyword into DB-optimized search terms
    - Make a SINGLE lightweight LLM call (no Google Search tool, no grounding) with a prompt like:
      ```
      You are a search query expander for a K-pop/fashion database.
      Given the keyword "{seed_keyword}", generate a JSON object with:
      - "search_keywords": list of 5-10 specific search terms optimized for DB text search
        (include: celeb names, group names, brand names, style terms, Korean equivalents)
      - "category_hints": list of relevant categories

      Focus on terms that would match artist_name, group_name, title, context fields in a posts table,
      and product names/brands in a solutions table.

      Return ONLY valid JSON.
      ```
    - Parse the response into a list of CuratedTopic dicts. Create ONE synthetic CuratedTopic with:
      - keyword = seed_keyword
      - related_keywords = the expanded search_keywords from LLM
      - celebrities = extracted celeb references from the search terms
      - brands_products = extracted brand references from the search terms
      - trend_background = f"AI-expanded DB search for: {seed_keyword}"
      - relevance_score = 1.0
      - sources = [] (no grounding sources)
    - Return `{"pipeline_status": "sourcing", "curated_topics": [topic_dict]}`
    - Use the existing `get_genai_client()` and model router with a new routing key `"curation_db_expand"` (fallback to default model if not configured)
    - Wrap in try/except like existing code; on failure, create a minimal CuratedTopic using just the raw seed_keyword and common splits of it

    **3. pipeline.py trigger_pipeline** - Add `elif body.mode == "ai_db_search":` block that creates initial_state with mode="ai_db_search" in curation_input (same structure as ai_curation, just different mode value). No pre-resolution needed -- curation_node and source_node handle everything.
    ```python
    elif body.mode == "ai_db_search":
        initial_state = {
            "thread_id": thread_id,
            "curation_input": {
                "seed_keyword": body.seed_keyword,
                "category": body.category,
                "tone": body.tone,
                "style": body.style,
                "mode": "ai_db_search",
            },
        }
    ```

    **Important:** source_node already handles the curated_topics -> DB search flow for ai_curation mode. The ai_db_search mode will produce curated_topics in the same format, so source_node needs NO changes for the basic flow. However, source_node currently skips when mode is "db_source" -- verify it does NOT skip for "ai_db_search" (it should fall through to the normal curated_topics search path, which it will since the skip condition checks for "db_source" specifically).
  </action>
  <verify>
    - `python -c "from editorial_ai.api.schemas import TriggerRequest; r = TriggerRequest(seed_keyword='test', mode='ai_db_search'); print(r.mode)"` prints "ai_db_search"
    - `python -c "from editorial_ai.nodes.curation import curation_node; print('ok')"` imports without error
    - `grep -n 'ai_db_search' src/editorial_ai/api/routes/pipeline.py src/editorial_ai/nodes/curation.py src/editorial_ai/api/schemas.py` shows matches in all 3 files
  </verify>
  <done>
    - TriggerRequest accepts mode="ai_db_search"
    - curation_node handles ai_db_search mode: calls LLM to expand keyword, returns synthetic curated_topics
    - pipeline trigger creates correct initial_state for ai_db_search mode
    - source_node naturally processes the curated_topics (no skip) and searches DB
  </done>
</task>

<task type="auto">
  <name>Task 2: Frontend - Add AI DB Search mode tab to new content modal</name>
  <files>
    admin/src/lib/types.ts
    admin/src/components/new-content-modal.tsx
  </files>
  <action>
    **1. types.ts** - Update TriggerRequest.mode union type:
    ```typescript
    mode?: "ai_curation" | "db_source" | "ai_db_search";
    ```

    **2. new-content-modal.tsx** - Add third mode tab and its form:

    a) Update ContentMode type:
    ```typescript
    type ContentMode = "ai_curation" | "db_source" | "ai_db_search";
    ```

    b) Add PIPELINE_STEPS for ai_db_search (same as PIPELINE_STEPS since it goes through curation+source+draft+review):
    ```typescript
    const PIPELINE_STEPS_AI_DB = [
      { key: "curating", label: "Expanding search terms" },
      { key: "sourcing", label: "Searching DB" },
      { key: "drafting", label: "Writing editorial" },
      { key: "reviewing", label: "Quality review" },
      { key: "awaiting_approval", label: "Ready for approval" },
    ] as const;
    ```

    c) Update the mode toggle to show 3 buttons. Use slightly shorter labels to fit:
    - "AI Curation" (existing)
    - "AI DB Search" (new - green/teal accent to distinguish)
    - "DB Source" (existing)

    d) Add the ai_db_search form section (renders when mode === "ai_db_search"). It should be SIMPLE -- very similar to ai_curation but with different placeholder text and description:
    - Keyword input (required) with placeholder "e.g., 선글라스 트렌드, NewJeans 공항패션"
    - A small helper text: "AI will expand your keyword into optimized search terms and find matching content from our database."
    - Category selector (same as ai_curation)
    - Advanced options (tone, style only -- no target_celeb/target_brand since AI handles that)
    - Submit button: "Search DB with AI"

    e) Update handleSubmit to handle ai_db_search mode:
    ```typescript
    // In the body construction:
    mode === "ai_db_search"
      ? {
          seed_keyword: keyword.trim(),
          category,
          mode: "ai_db_search" as const,
          ...(tone ? { tone } : {}),
          ...(style ? { style } : {}),
        }
      : mode === "db_source" ? { ... existing ... } : { ... existing ... }
    ```

    f) Update the `steps` variable to use PIPELINE_STEPS_AI_DB when mode is "ai_db_search":
    ```typescript
    const steps = mode === "db_source" ? PIPELINE_STEPS_DB : mode === "ai_db_search" ? PIPELINE_STEPS_AI_DB : PIPELINE_STEPS;
    ```

    g) Update the running phase description text to handle ai_db_search:
    ```typescript
    mode === "ai_db_search"
      ? ` searching DB for "${keyword}"`
      : mode === "db_source" ? ...existing... : ...existing...
    ```

    h) Update form validation in handleSubmit:
    ```typescript
    if ((mode === "ai_curation" || mode === "ai_db_search") && !keyword.trim()) return;
    ```
  </action>
  <verify>
    - `cd admin && npx tsc --noEmit` passes without type errors
    - `grep -n 'ai_db_search' admin/src/components/new-content-modal.tsx admin/src/lib/types.ts` shows matches in both files
  </verify>
  <done>
    - Third "AI DB Search" tab visible in mode toggle
    - ai_db_search form shows keyword input + category + advanced (tone/style)
    - Submit sends mode="ai_db_search" to trigger endpoint
    - Pipeline progress shows appropriate step labels for ai_db_search mode
    - TypeScript compiles without errors
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    Complete ai_db_search pipeline mode: user enters keyword in admin UI -> AI expands to DB search terms -> source_node searches internal DB -> editorial content generated from found sources.
  </what-built>
  <how-to-verify>
    1. Open admin UI (http://localhost:3000)
    2. Click "New Content"
    3. Verify three mode tabs visible: "AI Curation" | "AI DB Search" | "DB Source"
    4. Select "AI DB Search" tab
    5. Enter a keyword like "선글라스" or "NewJeans"
    6. Click "Search DB with AI"
    7. Watch pipeline progress: "Expanding search terms" -> "Searching DB" -> "Writing editorial" -> "Quality review"
    8. Verify content is created with data sourced from the internal DB (check the content detail page for real celeb/product references)
    9. Compare with regular "AI Curation" mode to confirm ai_db_search is faster (no Google Search grounding)
  </how-to-verify>
  <resume-signal>Type "approved" or describe any issues with the flow</resume-signal>
</task>

</tasks>

<verification>
- Backend: `python -c "from editorial_ai.nodes.curation import curation_node; from editorial_ai.api.schemas import TriggerRequest; print('imports ok')"`
- Frontend: `cd admin && npx tsc --noEmit` passes
- Integration: Trigger via curl and verify pipeline completes:
  ```bash
  curl -X POST http://localhost:8000/api/pipeline/trigger \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{"seed_keyword": "선글라스 트렌드", "category": "fashion", "mode": "ai_db_search"}'
  ```
</verification>

<success_criteria>
- ai_db_search mode produces editorial content using only DB sources (no external search)
- LLM call in curation_node expands keyword into relevant DB search terms
- source_node finds posts/solutions matching the expanded terms
- Admin UI provides clean UX for the new mode with appropriate progress labels
- All three modes (ai_curation, ai_db_search, db_source) work independently
</success_criteria>

<output>
After completion, create `.planning/quick/002-db-keyword-curation-source/002-SUMMARY.md`
</output>
