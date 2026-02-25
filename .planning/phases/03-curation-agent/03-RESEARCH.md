# Phase 3: Curation Agent - Research

**Researched:** 2026-02-25
**Domain:** Gemini Google Search Grounding + LangGraph node integration
**Confidence:** MEDIUM

## Summary

Phase 3 implements a curation node that takes a single seed keyword and produces multiple structured `curated_topics` entries by calling Gemini with Google Search Grounding. The core technical challenge is the **incompatibility between Google Search Grounding and structured output (JSON schema mode)** -- these cannot be used simultaneously in the current Gemini 2.5 API. This requires a two-step approach: (1) grounded text generation, (2) structured JSON extraction.

The project has two Google GenAI SDK options: the native `google-genai` SDK (used in `scripts/test_grounding.py`) and `langchain-google-genai` (used in the existing LLM factory). Both support Google Search Grounding, but grounding metadata access differs. The native SDK provides cleaner grounding metadata extraction, while `langchain-google-genai` recently added metadata support (PR #944, post v4.2.1).

**Primary recommendation:** Use the native `google-genai` SDK directly for the curation service layer (grounding + metadata extraction), and Pydantic for output validation. Do not force LangChain wrappers where the native SDK is simpler and more reliable for this specific use case. The curation LangGraph node calls this service and writes to pipeline state.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `google-genai` | 1.64.0 | Gemini API client with Google Search Grounding | Already installed; native grounding support with metadata; async via `client.aio`; tested in `scripts/test_grounding.py` |
| `langgraph` | 1.0.9 | Graph node orchestration | Already the pipeline framework; curation node plugs into existing graph |
| `pydantic` | 2.12.5 | Output validation for curated topic structure | Already used project-wide; `model_validate` for JSON parsing |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tenacity` | 9.1.4 | Retry with exponential backoff | Already installed (transitive dep); wrap API calls |
| `langchain-google-genai` | 4.2.1 | Existing LLM factory | Continue using for non-grounding LLM calls in other phases; NOT recommended for grounding due to metadata access complexity |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native `google-genai` for grounding | `langchain-google-genai` with `bind_tools([{"google_search": {}}])` | LangChain bind_tools supports grounding, but metadata extraction is less straightforward; grounding_metadata in response_metadata was only merged in PR #944 (post May 2025) and may not be in v4.2.1; native SDK is proven in test script |
| `tenacity` for retries | `google.genai.retry.RetryConfig` on Client | Client-level retry config exists but is less flexible; `tenacity` allows per-call customization and is already available |
| Prompt-based JSON extraction | `with_structured_output()` | Cannot combine structured output with grounding tools in Gemini 2.5; prompt-based JSON + Pydantic validation is the only viable path |

**Installation:** No new packages needed. All required libraries are already installed.

## Architecture Patterns

### Recommended Project Structure
```
src/editorial_ai/
├── services/
│   └── curation_service.py    # Gemini grounding API calls + response parsing
├── nodes/
│   ├── stubs.py               # Existing stubs (curation stub to be replaced)
│   └── curation.py            # LangGraph curation node (calls service, writes state)
├── models/
│   └── curation.py            # Pydantic models for CuratedTopic, CurationResult
├── prompts/
│   └── curation.py            # Prompt templates for trend research + topic expansion
├── llm.py                     # Existing (unchanged)
├── state.py                   # Existing (curation_input, curated_topics already defined)
└── graph.py                   # Wire real curation node via node_overrides or direct import
```

### Pattern 1: Two-Step Grounding + Extraction
**What:** Separate the grounded search call from JSON extraction because Gemini 2.5 cannot combine Google Search Grounding with structured output (`response_schema`).
**When to use:** Any call requiring both web-grounded responses AND structured JSON output.
**Example:**
```python
# Source: https://github.com/googleapis/python-genai/issues/665
# Step 1: Grounded text generation (with sources)
grounded_response = await client.aio.models.generate_content(
    model="gemini-2.5-flash",
    contents=trend_research_prompt,
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.7,
    ),
)
raw_text = grounded_response.text
sources = extract_grounding_sources(grounded_response)

# Step 2: Structured extraction (no grounding, use JSON prompt)
extraction_response = await client.aio.models.generate_content(
    model="gemini-2.5-flash",
    contents=f"Extract structured data from this research:\n{raw_text}\n\nReturn JSON...",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.0,
    ),
)
topic = CuratedTopic.model_validate_json(extraction_response.text)
```

### Pattern 2: Service Layer Encapsulation
**What:** Encapsulate all Gemini API interaction in a service class. The LangGraph node only calls the service and writes to state.
**When to use:** Always. Keeps node functions thin and testable.
**Example:**
```python
# services/curation_service.py
class CurationService:
    def __init__(self, client: genai.Client):
        self.client = client

    async def research_trend(self, keyword: str) -> TrendResearch:
        """Step 1: Grounded trend research."""
        ...

    async def expand_subtopics(self, keyword: str, background: str) -> list[str]:
        """Generate sub-topic keywords from seed."""
        ...

    async def curate_topic(self, keyword: str) -> CuratedTopic:
        """Full pipeline: research + extract + validate."""
        ...

    async def curate_seed(self, seed_keyword: str) -> CurationResult:
        """Entry point: seed -> multiple curated topics."""
        ...

# nodes/curation.py
async def curation_node(state: EditorialPipelineState) -> dict:
    service = CurationService(get_genai_client())
    result = await service.curate_seed(state["curation_input"]["keyword"])
    return {
        "pipeline_status": "sourcing",
        "curated_topics": [t.model_dump() for t in result.topics],
    }
```

### Pattern 3: Grounding Metadata Extraction
**What:** Extract source URLs from grounding metadata for the `sources` field.
**When to use:** After every grounded API call.
**Example:**
```python
# Source: https://ai.google.dev/gemini-api/docs/google-search
def extract_grounding_sources(response) -> list[dict]:
    """Extract source URLs and titles from grounding metadata."""
    sources = []
    if (response.candidates
        and response.candidates[0].grounding_metadata
        and response.candidates[0].grounding_metadata.grounding_chunks):
        for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
            if chunk.web:
                sources.append({
                    "url": chunk.web.uri,
                    "title": chunk.web.title,
                })
    return sources
```

### Pattern 4: Async Node in LangGraph
**What:** LangGraph nodes can be async functions. The graph invocation uses `ainvoke()`.
**When to use:** When the node makes async API calls.
**Example:**
```python
async def curation_node(state: EditorialPipelineState) -> dict:
    """Async curation node - calls Gemini API."""
    ...
    return {"curated_topics": [...], "pipeline_status": "sourcing"}

# In graph.py or tests
result = await graph.ainvoke(initial_state)
```

### Anti-Patterns to Avoid
- **Combining grounding + structured output in one call:** Gemini 2.5 does not support `response_schema` with `google_search` tool. Will error with "controlled generation is not supported with google_search tool."
- **Wrapping native SDK in LangChain for grounding calls:** Adds complexity without benefit; grounding metadata access through LangChain is fragile.
- **Putting API call logic directly in node functions:** Makes testing require API mocking at the wrong layer. Service class enables clean unit tests.
- **Storing full grounded text in pipeline state:** Violates lean state principle. Store structured `curated_topics` only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff | Custom retry loops | `tenacity` `@retry` decorator | Handles jitter, max attempts, exception filtering; already installed |
| JSON parsing + validation | Manual dict construction | Pydantic `model_validate_json()` | Type safety, field validation, error messages |
| Async API client lifecycle | Manual open/close | `async with client.aio as aclient:` | Context manager guarantees cleanup |
| Source URL extraction | Regex on response text | `response.candidates[0].grounding_metadata.grounding_chunks` | SDK provides structured metadata |

**Key insight:** The Gemini grounding response already contains structured metadata (sources, search queries). Don't parse the text for URLs -- use the SDK's metadata objects.

## Common Pitfalls

### Pitfall 1: Grounding + Structured Output Incompatibility
**What goes wrong:** Attempting to use `response_mime_type="application/json"` + `response_schema` together with `google_search` tool raises an error.
**Why it happens:** Gemini 2.5 API limitation -- "controlled generation is not supported with google_search tool." This was supported in Gemini 2.0 but regressed in 2.5.
**How to avoid:** Two-step pattern: grounded call for research, separate call for JSON extraction.
**Warning signs:** `APIError` with message about controlled generation not supported.

### Pitfall 2: Empty Grounding Metadata
**What goes wrong:** `grounding_metadata` is `None` or has empty `grounding_chunks` even with grounding enabled.
**Why it happens:** (a) Model decided no search was needed, (b) search returned no results, (c) short/simple queries.
**How to avoid:** Always check for `None` at each level. Treat missing metadata gracefully -- set `sources: []` and optionally flag `low_quality: true`.
**Warning signs:** `AttributeError` when accessing nested grounding fields.

### Pitfall 3: JSON Parsing Failures from Prompt-Based Extraction
**What goes wrong:** Model returns text with markdown code fences, extra text, or malformed JSON despite prompt instructions.
**Why it happens:** Without formal `response_schema`, model may not strictly comply with JSON format.
**How to avoid:** (a) Use `response_mime_type="application/json"` on the extraction step (without grounding). (b) Strip markdown code fences as fallback. (c) Pydantic `model_validate_json()` gives clear errors.
**Warning signs:** `json.JSONDecodeError` or Pydantic `ValidationError`.

### Pitfall 4: Rate Limiting on Grounding Calls
**What goes wrong:** 429 errors with "RESOURCE_EXHAUSTED" when making multiple grounded calls in sequence.
**Why it happens:** Gemini 2.5 Flash has per-minute rate limits; grounding calls count against quota; topic expansion generates multiple API calls.
**How to avoid:** (a) `tenacity` retry with exponential backoff. (b) Consider sequential (not parallel) sub-topic calls to avoid burst. (c) Small delay between calls.
**Warning signs:** `google.genai.errors.ClientError` with code 429.

### Pitfall 5: Lean State Violation
**What goes wrong:** Storing full grounded text, prompt content, or intermediate research in `curated_topics`.
**Why it happens:** Natural to want to preserve all context.
**How to avoid:** Only store the final structured topic data in state. Keep `curated_topics` entries to the defined schema (keyword, trend_background, related_keywords, celebrities, brands_products, seasonality, sources).
**Warning signs:** State size exceeding 10KB threshold established in Phase 2.

## Code Examples

### Creating the Gemini Client for Grounding
```python
# Source: scripts/test_grounding.py (project reference)
from google import genai
from editorial_ai.config import settings

def get_genai_client() -> genai.Client:
    """Create a google-genai Client using project settings."""
    return genai.Client(api_key=settings.google_api_key)
```

### Retry Decorator for API Calls
```python
# Source: tenacity documentation + google.genai.errors
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.genai.errors import ClientError, ServerError

retry_on_api_error = retry(
    retry=retry_if_exception_type((ClientError, ServerError)),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(3),
    reraise=True,
)
```

### Pydantic Models for Curated Topic
```python
# Source: CONTEXT.md decisions (locked structure)
from pydantic import BaseModel, Field

class CelebReference(BaseModel):
    name: str
    relevance: str

class BrandReference(BaseModel):
    name: str
    relevance: str

class GroundingSource(BaseModel):
    url: str
    title: str | None = None

class CuratedTopic(BaseModel):
    keyword: str
    trend_background: str
    related_keywords: list[str]
    celebrities: list[CelebReference]
    brands_products: list[BrandReference]
    seasonality: str
    sources: list[GroundingSource] = Field(default_factory=list)
    relevance_score: float = Field(ge=0.0, le=1.0, description="0-1 trend relevance score")
    low_quality: bool = False
```

### Async Grounded API Call
```python
# Source: https://github.com/googleapis/python-genai README
from google import genai
from google.genai import types

async def grounded_generate(client: genai.Client, prompt: str) -> types.GenerateContentResponse:
    """Make a grounded Gemini call using async client."""
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.7,
        ),
    )
    return response
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `google-generativeai` SDK (deprecated) | `google-genai` unified SDK | 2025 | New SDK supports both Developer API and Vertex AI; old SDK deprecated |
| `google_search_retrieval` tool type | `google_search` tool type | Gemini 2.0+ | Older models use different tool name |
| Grounding + structured output in one call | Two-step: grounding then extraction | Gemini 2.5 regression | Gemini 2.0 supported both; 2.5 does not |
| `langchain-google-genai` v2.x (legacy SDK) | v4.x (uses `google-genai` internally) | v4.0.0 (Dec 2024) | Major rewrite; now wraps the same `google-genai` SDK |

**Deprecated/outdated:**
- `google-generativeai` package: Replaced by `google-genai`. Migration guide at https://ai.google.dev/gemini-api/docs/migrate
- `google_search_retrieval` tool: Use `google_search` for Gemini 2.0+ models

## Discretion Recommendations

### Topic Expansion Count
**Recommendation:** 3-7 sub-topics per seed keyword.
**Rationale:** Narrow keywords (e.g., "Y2K 디님") produce 3-4 meaningful sub-topics. Broad keywords (e.g., "2026 S/S") may produce 5-7. Let Gemini suggest sub-topics in the first grounded call, then cap at 7 to limit API calls.

### Retry Strategy
**Recommendation:** 3 attempts, exponential backoff (1s, 2s, 4s), retry on 429 and 5xx errors.
**Rationale:** Gemini Developer API free tier has strict rate limits. 3 attempts is enough for transient issues without excessive delay. Total max wait: ~7s per call.

### DB Matching Timing
**Recommendation:** Defer to Phase 5. Curation produces names/text only -- DB matching requires fuzzy search logic that belongs in the Source/Enrichment phase.
**Rationale:** Clean separation of concerns. Curation focuses on trend discovery, not data enrichment.

### Relevance Score Threshold
**Recommendation:** 0.6 threshold. Topics scoring below 0.6 are excluded from `curated_topics`.
**Rationale:** In a 0-1 scale, 0.6 filters out tangentially related topics while keeping reasonably relevant ones. This can be tuned later. Include the threshold as a configurable constant.

## Open Questions

1. **Duplicate Detection Across Runs**
   - What we know: CONTEXT.md says "같은 키워드로 재실행 시 이전 결과 참조하여 중복 토픽 제외"
   - What's unclear: How to access previous results. Checkpointer stores graph state per thread_id, but querying past curated_topics for a keyword requires either a separate lookup or consistent thread_id naming.
   - Recommendation: For Phase 3, implement keyword-based dedup within a single run (don't produce duplicate sub-topics). Cross-run dedup can be deferred to a future iteration when a persistence layer for curation history is established.

2. **Gemini Model Selection for Grounding**
   - What we know: `gemini-2.5-flash` used in test script; project default is `gemini-2.5-flash`.
   - What's unclear: Whether `gemini-2.5-flash` will remain available or if Google will promote `gemini-3-flash` variants.
   - Recommendation: Use `settings.default_model` (currently `gemini-2.5-flash`). Make model configurable in the service layer.

3. **Billing Impact of Grounding**
   - What we know: Gemini 2.5 models are billed per prompt (not per search query). Gemini 3 changes to per-query billing.
   - What's unclear: Exact cost per grounded call at current usage tier.
   - Recommendation: Monitor via LangSmith tracing. Log API call counts for cost estimation.

## Sources

### Primary (HIGH confidence)
- `scripts/test_grounding.py` -- Verified working pattern in the project
- `src/editorial_ai/` codebase -- Existing architecture, patterns, state shape
- https://ai.google.dev/gemini-api/docs/google-search -- Official Gemini grounding docs

### Secondary (MEDIUM confidence)
- https://github.com/googleapis/python-genai/issues/665 -- Structured output + grounding incompatibility confirmed by Google team (closed as known limitation)
- https://github.com/langchain-ai/langchain-google/issues/825 -- Grounding metadata support in langchain-google-genai (PR #944 merged)
- https://github.com/langchain-ai/langchain-google/issues/1071 -- Native Google tools with langchain-google
- https://github.com/googleapis/python-genai -- Async client documentation (client.aio)
- https://github.com/langchain-ai/langchain-google/releases -- Release notes for v4.2.x

### Tertiary (LOW confidence)
- https://www.cennest.com/making-sense-of-the-gemini-2-5-flash-with-google-grounding-source-urls/ -- Two-step workaround blog post
- https://geminibyexample.com/029-rate-limits-retries/ -- Retry config pattern (uses deprecated SDK import paths)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Libraries already installed and tested in project
- Architecture: MEDIUM -- Two-step pattern is well-documented as workaround but not officially "recommended"
- Pitfalls: HIGH -- Grounding+structured output incompatibility confirmed by Google team in GitHub issue
- Retry patterns: MEDIUM -- tenacity is standard; google-genai error classes verified from source

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (30 days; Gemini API evolves rapidly, re-check grounding+structured output compatibility)
