# Phase 5: Editorial Agent - DB Tools - Research

**Researched:** 2026-02-25
**Domain:** Supabase DB search + Gemini keyword expansion + LangGraph enrich node
**Confidence:** HIGH

## Summary

This phase adds a new `enrich_editorial` LangGraph node between `editorial` and `review` that enriches the Phase 4 draft with real celeb/product data from Supabase. The architecture is straightforward: the existing `celeb_service` and `product_service` already provide `search_celebs()` and `search_products()` with `ilike` matching. This phase extends those services with multi-column OR search and tag-based matching, adds a Gemini keyword expansion step, then builds a new node that (1) extracts mentions from the current draft, (2) expands keywords via Gemini, (3) searches Supabase with both mention names and expanded keywords, (4) regenerates the content with DB results as context.

The existing codebase already has the Pydantic models (`Celeb`, `Product`), service functions, Supabase async client, and layout models (`CelebItem`, `ProductItem` with `celeb_id`/`product_id` placeholders designed for exactly this phase). The `EditorialContent` model has `celeb_mentions` and `product_mentions` fields. The `MagazineLayout` has `CelebFeatureBlock` and `ProductShowcaseBlock` with ID fields ready for DB linking.

**Primary recommendation:** Build a standalone `enrich_editorial` node that calls enhanced search services and Gemini re-generation, keeping `editorial_node` from Phase 4 completely untouched.

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| supabase | 2.28.0 | Async DB client for Supabase REST API | Already installed, provides `ilike`, `or_`, `contains` filters |
| google-genai (via `google.genai`) | (installed) | Keyword expansion + content regeneration | Native SDK already used in editorial_service and curation_service |
| langgraph | >=1.0.9 | Graph node for enrichment step | Already used for pipeline orchestration |
| pydantic | >=2.12.5 | Data validation for search results and enriched content | Already used throughout |

### Supporting (Already in Project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | (via curation_service) | Retry decorator for API calls | Wrap Gemini keyword expansion calls |

### No New Dependencies Required
This phase requires zero new dependencies. Everything needed is already installed.

## Architecture Patterns

### Recommended Project Structure (New Files)
```
src/editorial_ai/
├── services/
│   ├── celeb_service.py       # EXTEND: add search_celebs_multi(), search_celebs_by_tags()
│   ├── product_service.py     # EXTEND: add search_products_multi(), search_products_by_tags()
│   └── enrich_service.py      # NEW: keyword expansion + DB search orchestration + re-generation
├── nodes/
│   └── enrich.py              # NEW: enrich_editorial node
├── prompts/
│   └── enrich.py              # NEW: keyword expansion + re-generation prompts
└── state.py                   # MODIFY: add enrichment-related state fields (optional)
```

### Pattern 1: Multi-Column OR Search on Supabase
**What:** Search celebs/products across name, description, and tags using `or_()` with PostgREST syntax
**When to use:** When a single keyword should match against multiple columns
**Example:**
```python
# Source: Supabase Python docs - or_ filter
async def search_celebs_multi(query: str, *, limit: int = 10) -> list[Celeb]:
    """Search celebs across name, name_en, description using OR."""
    client = await get_supabase_client()
    pattern = f"%{query}%"
    response = await (
        client.table("celebs")
        .select("*")
        .or_(f"name.ilike.{pattern},name_en.ilike.{pattern},description.ilike.{pattern}")
        .limit(limit)
        .execute()
    )
    return [Celeb.model_validate(row) for row in response.data]
```

### Pattern 2: Tag-Based Array Search on Supabase
**What:** Search using `contains` filter on the `tags` array column
**When to use:** When expanded keywords should match tag arrays
**Example:**
```python
# Source: Supabase Python docs - contains filter
async def search_celebs_by_tags(tags: list[str], *, limit: int = 10) -> list[Celeb]:
    """Search celebs where tags array contains any of the given tags."""
    client = await get_supabase_client()
    # Use or_ to match any single tag (contains requires ALL)
    conditions = ",".join(f"tags.cs.{{{tag}}}" for tag in tags)
    response = await (
        client.table("celebs")
        .select("*")
        .or_(conditions)
        .limit(limit)
        .execute()
    )
    return [Celeb.model_validate(row) for row in response.data]
```

### Pattern 3: Enrich Node as Separate LangGraph Node
**What:** A standalone node between `editorial` and `review` in the graph
**When to use:** This is the decided architecture from CONTEXT.md
**Example:**
```python
# editorial -> enrich -> review (modify graph.py edges)
builder.add_edge("editorial", "enrich")
builder.add_edge("enrich", "review")
```

### Pattern 4: Gemini Keyword Expansion (Reuse Existing Pattern)
**What:** Use the same native google-genai SDK pattern from curation_service for keyword expansion
**When to use:** Before DB search to broaden search coverage
**Example:**
```python
# Reuse curation_service utilities
from editorial_ai.services.curation_service import (
    get_genai_client, retry_on_api_error, _strip_markdown_fences,
)

@retry_on_api_error
async def expand_keywords(client: genai.Client, keyword: str) -> list[str]:
    """Expand a keyword into related search terms using Gemini."""
    response = await client.aio.models.generate_content(
        model=settings.default_model,
        contents=f"키워드 '{keyword}'에서 패션/셀럽/브랜드와 관련된 연관 검색어를 5-10개 생성. JSON 배열로.",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )
    raw = _strip_markdown_fences(response.text or "[]")
    terms = json.loads(raw)
    return [str(t) for t in terms] if isinstance(terms, list) else []
```

### Pattern 5: Content Re-generation with DB Context
**What:** Pass DB celeb/product data to Gemini to regenerate editorial content with real references
**When to use:** After DB search results are collected
**Example:**
```python
# Re-generate with enriched context
async def regenerate_with_enrichment(
    client: genai.Client,
    original_content: EditorialContent,
    celebs: list[Celeb],
    products: list[Product],
    keyword: str,
) -> EditorialContent:
    """Regenerate editorial content with actual DB celeb/product data."""
    prompt = build_enrichment_regeneration_prompt(
        original_content, celebs, products, keyword
    )
    response = await client.aio.models.generate_content(
        model=settings.editorial_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=EditorialContent,
            temperature=0.7,
        ),
    )
    return EditorialContent.model_validate_json(response.text or "{}")
```

### Pattern 6: Deduplication of Search Results
**What:** Combine results from mention-name search + keyword-expansion search, deduplicate by ID
**When to use:** When merging parallel search results
**Example:**
```python
def deduplicate_by_id(items: list[Celeb]) -> list[Celeb]:
    """Remove duplicate items, preserving order of first occurrence."""
    seen: set[str] = set()
    result: list[Celeb] = []
    for item in items:
        if item.id not in seen:
            seen.add(item.id)
            result.append(item)
    return result
```

### Anti-Patterns to Avoid
- **Modifying editorial_node:** The decision is to keep Phase 4 editorial_node untouched. All enrichment logic goes in the new enrich node.
- **Blocking on missing DB data:** If no celebs/products are found, return the original draft unchanged (graceful degradation).
- **Sequential single-keyword searches:** Batch multiple search queries with asyncio.gather for parallel execution.
- **Hardcoding celeb/product counts:** Let the content and DB results determine quantity naturally.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-column text search | Custom SQL or multiple separate queries | Supabase `or_()` with PostgREST syntax | Single query, server-side optimization |
| Retry logic for Gemini calls | Custom try/except retry loops | `retry_on_api_error` from curation_service (tenacity) | Already battle-tested in codebase |
| JSON parsing with fence stripping | New utility | `_strip_markdown_fences` from curation_service | Already handles edge cases |
| Pydantic validation with repair | Custom validation | `_validate_with_repair` pattern from editorial_service | Already handles Gemini output quirks |
| ID-based deduplication | Set operations on dicts | Simple seen-set pattern on Pydantic model .id | Clean, type-safe |

**Key insight:** This phase heavily reuses patterns and utilities from Phase 3 (curation_service) and Phase 4 (editorial_service). The keyword expansion is structurally identical to `expand_subtopics()` in curation_service. The re-generation is structurally identical to `generate_content()` in editorial_service.

## Common Pitfalls

### Pitfall 1: Supabase `or_()` PostgREST Syntax Errors
**What goes wrong:** The `or_()` method uses raw PostgREST string syntax, not Python chaining. Misformatted strings silently fail or return empty results.
**Why it happens:** PostgREST syntax like `name.ilike.%query%` looks unusual and is easy to misformat.
**How to avoid:** Unit test each search function with mocked client verifying the exact `or_()` string passed. Use constants for column names.
**Warning signs:** Search returns empty results when data exists; no error raised.

### Pitfall 2: Gemini Keyword Expansion Returning Non-Fashion Terms
**What goes wrong:** Gemini expands "Y2K" into generic terms like "year 2000" or "technology" instead of fashion terms like "레트로, 빈티지, 로우라이즈".
**Why it happens:** Prompt doesn't constrain the domain tightly enough.
**How to avoid:** Explicitly constrain the prompt to fashion/celebrity/brand domain. Include examples in the prompt.
**Warning signs:** DB search returns irrelevant results despite correct query mechanics.

### Pitfall 3: Tags Column Not Existing or Having Different Format
**What goes wrong:** The `tags` column in Celeb/Product models is assumed to be `list[str]` but the actual Supabase schema may differ.
**Why it happens:** Models were created with "domain-reasonable defaults" per Phase 2 decision, schema not yet verified.
**How to avoid:** Write search functions that gracefully handle missing tags column. Use `ilike` on name/description as primary, tags as optional enhancement. Add integration test marked `@pytest.mark.integration`.
**Warning signs:** `contains` filter raises error on execution.

### Pitfall 4: Re-generation Losing Original Content Quality
**What goes wrong:** The Gemini re-generation produces content that's lower quality than the original draft because it tries to force-fit DB results.
**Why it happens:** Re-generation prompt doesn't preserve enough of the original content structure and tone.
**How to avoid:** Pass the FULL original content as context to the re-generation prompt. Instruct Gemini to maintain tone, structure, and quality while naturally incorporating the enrichment data.
**Warning signs:** Re-generated content reads like a product catalog instead of an editorial.

### Pitfall 5: Graph Edge Modification Breaking Existing Tests
**What goes wrong:** Changing `editorial -> review` to `editorial -> enrich -> review` breaks test_graph.py tests.
**Why it happens:** Tests assert specific graph topology.
**How to avoid:** Update graph tests to expect the new topology. Use `node_overrides` to inject a stub enrich node in tests that don't need real enrichment.
**Warning signs:** Test failures in test_graph.py after modifying graph.py.

### Pitfall 6: Empty DB Results Causing Enrich Node Failure
**What goes wrong:** When no celebs or products match, the enrich node errors out instead of passing through the original draft.
**Why it happens:** Code assumes search will always return results.
**How to avoid:** Explicit empty-result check. If no results found, return original draft with no changes. This is a success criteria requirement.
**Warning signs:** Pipeline fails on niche keywords with no DB matches.

## Code Examples

### Enhanced Celeb Search Service
```python
# Source: Existing celeb_service.py pattern + Supabase or_ docs
async def search_celebs_multi(
    queries: list[str], *, limit: int = 10
) -> list[Celeb]:
    """Search celebs across name, name_en, description for multiple queries."""
    client = await get_supabase_client()
    all_results: list[Celeb] = []

    for query in queries:
        pattern = f"%{query}%"
        response = await (
            client.table("celebs")
            .select("*")
            .or_(f"name.ilike.{pattern},name_en.ilike.{pattern},description.ilike.{pattern}")
            .limit(limit)
            .execute()
        )
        all_results.extend(Celeb.model_validate(row) for row in response.data)

    return deduplicate_by_id(all_results)
```

### Enrich Node Skeleton
```python
# Source: Existing editorial_node pattern
async def enrich_editorial_node(state: EditorialPipelineState) -> dict:
    """LangGraph node: enrich editorial draft with DB celeb/product data."""
    current_draft = state.get("current_draft")
    if not current_draft:
        return {"error_log": ["Enrich skipped: no current_draft"]}

    layout = MagazineLayout.model_validate(current_draft)

    # 1. Extract mentions from draft
    celeb_names = extract_celeb_names(layout)
    product_names = extract_product_names(layout)

    # 2. Expand keywords via Gemini
    keyword = layout.keyword
    client = get_genai_client()
    expanded = await expand_keywords(client, keyword)

    # 3. Search DB (mention names + expanded keywords)
    search_terms_celeb = celeb_names + expanded
    search_terms_product = product_names + expanded

    celebs = await search_celebs_multi(search_terms_celeb, limit=10)
    products = await search_products_multi(search_terms_product, limit=10)

    # 4. If no results, return original draft
    if not celebs and not products:
        return {}  # No state changes = original draft preserved

    # 5. Regenerate content with DB context
    enriched_content = await regenerate_with_enrichment(
        client, layout, celebs, products, keyword
    )

    # 6. Rebuild layout with DB IDs
    enriched_layout = rebuild_layout_with_db_data(layout, enriched_content, celebs, products)

    return {"current_draft": enriched_layout.model_dump()}
```

### Extracting Mentions from Layout
```python
def extract_celeb_names(layout: MagazineLayout) -> list[str]:
    """Extract celeb names from CelebFeatureBlock blocks."""
    names: list[str] = []
    for block in layout.blocks:
        if isinstance(block, CelebFeatureBlock):
            names.extend(c.name for c in block.celebs)
    return names

def extract_product_names(layout: MagazineLayout) -> list[str]:
    """Extract product names from ProductShowcaseBlock blocks."""
    names: list[str] = []
    for block in layout.blocks:
        if isinstance(block, ProductShowcaseBlock):
            names.extend(p.name for p in block.products)
    return names
```

### Rebuilding Layout with DB IDs
```python
def rebuild_layout_with_db_data(
    layout: MagazineLayout,
    enriched_content: EditorialContent,
    celebs: list[Celeb],
    products: list[Product],
) -> MagazineLayout:
    """Rebuild layout blocks with actual DB IDs and details."""
    new_layout = deepcopy(layout)

    # Build lookup maps
    celeb_map = {c.name.lower(): c for c in celebs}
    product_map = {p.name.lower(): p for p in products}

    for block in new_layout.blocks:
        if isinstance(block, CelebFeatureBlock):
            block.celebs = [
                CelebItem(
                    celeb_id=celeb_map.get(cm.name.lower(), Celeb(id="", name=cm.name)).id or None,
                    name=cm.name,
                    image_url=celeb_map.get(cm.name.lower(), Celeb(id="", name="")).profile_image_url,
                    description=cm.context,
                )
                for cm in enriched_content.celeb_mentions
            ]
        elif isinstance(block, ProductShowcaseBlock):
            block.products = [
                ProductItem(
                    product_id=product_map.get(pm.name.lower(), Product(id="", name=pm.name)).id or None,
                    name=pm.name,
                    brand=pm.brand,
                    image_url=product_map.get(pm.name.lower(), Product(id="", name="")).image_url,
                    description=pm.context,
                )
                for pm in enriched_content.product_mentions
            ]
        elif isinstance(block, BodyTextBlock):
            block.paragraphs = enriched_content.body_paragraphs

    return new_layout
```

### Mock Pattern for Enrich Service Tests
```python
# Source: Existing test_services.py pattern
def _build_mock_client_or(response_data: list) -> MagicMock:
    """Build mock client that supports or_ chaining."""
    mock_client = MagicMock()
    builder = MagicMock()
    builder.select.return_value = builder
    builder.or_.return_value = builder  # Add or_ support
    builder.limit.return_value = builder
    builder.execute = AsyncMock(return_value=_mock_response(response_data))
    mock_client.table.return_value = builder
    return mock_client
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangChain tool binding for DB access | Direct async service calls in node | Project decision (Phase 5 context) | Simpler, no tool binding overhead; Claude's discretion item resolved |
| Single `ilike` on name column | `or_()` across name + description + tags | This phase | Broader search coverage |
| Manual keyword list | Gemini keyword expansion | This phase | Automated, context-aware term generation |

**Decision on Tool binding vs Direct service calls:** Based on the codebase analysis, the project already uses direct service calls (not LangChain tool binding) for all Supabase operations. The `celeb_service.py` and `product_service.py` are simple async functions, not LangChain tools. The `editorial_service.py` uses native google-genai SDK directly, not through LangChain. **Recommendation: Use direct service calls** -- consistent with existing patterns, simpler, and avoids adding LangChain tool binding complexity for what is essentially a deterministic DB lookup step (not an agent decision).

## Open Questions

1. **Actual Supabase table schema**
   - What we know: Models were created with "domain-reasonable defaults" (Phase 2 decision). Fields like `tags`, `name_en`, `category` may not exist.
   - What's unclear: Whether the actual tables have these columns, or have additional useful columns for search.
   - Recommendation: Write search functions that work with the assumed schema but handle missing columns gracefully. Integration tests will validate when credentials are available. The `ilike` on `name` is the safest minimum viable search.

2. **Korean full-text search support**
   - What we know: Supabase supports PostgreSQL full-text search with `text_search()` but it requires `tsvector` columns and language configuration. Korean requires special configuration (not default).
   - What's unclear: Whether the Supabase instance has Korean text search configured.
   - Recommendation: Use `ilike` pattern matching (already proven in codebase) rather than `text_search()`. `ilike` works for Korean without special configuration. Full-text search can be added later as an optimization.

3. **Re-generation prompt quality**
   - What we know: The prompt needs to preserve editorial tone while incorporating DB data naturally.
   - What's unclear: Exact prompt wording that produces best results.
   - Recommendation: Start with a clear prompt that provides original content + DB data + instructions. Iterate based on output quality.

## Sources

### Primary (HIGH confidence)
- Supabase Python docs - `or_()` filter: https://supabase.com/docs/reference/python/or
- Supabase Python docs - `ilike` filter: https://supabase.com/docs/reference/python/ilike
- Supabase Python docs - `contains` filter: https://supabase.com/docs/reference/python/contains
- Supabase Python docs - `text_search`: https://supabase.com/docs/reference/python/textsearch
- Existing codebase: `celeb_service.py`, `product_service.py`, `editorial_service.py`, `curation_service.py` patterns

### Secondary (MEDIUM confidence)
- Supabase discussion on multi-column ilike: https://github.com/orgs/supabase/discussions/6778
- Supabase issue on chaining ilike with or_: https://github.com/supabase/supabase-py/issues/789

### Tertiary (LOW confidence)
- LangGraph data enrichment patterns (general guidance): https://github.com/langchain-ai/data-enrichment

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already installed and used in project
- Architecture: HIGH - Follows existing node/service/prompt patterns exactly
- Supabase search patterns: HIGH - Verified with official Python docs
- Pitfalls: MEDIUM - Based on codebase analysis + community discussions
- DB schema compatibility: LOW - Actual schema not verified (no credentials)

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable -- no fast-moving dependencies)
