# Phase 13: Pipeline Advanced - Research

**Researched:** 2026-02-26
**Domain:** Gemini model routing, context caching, adaptive evaluation rubrics
**Confidence:** MEDIUM-HIGH

## Summary

Phase 13 adds three advanced capabilities to the editorial pipeline: dynamic model routing (selecting Gemini Pro/Flash/Flash-Lite per node based on task complexity), context caching (reusing repeated source documents across pipeline runs), and adaptive rubrics (adjusting review criteria by content type).

The codebase already uses the `google-genai` SDK v1.64.0 directly for all LLM calls (not LangChain wrappers), which provides native support for context caching via `client.caches.create()` and `client.aio.caches.create()`. No SDK migration to Vertex AI SDK is needed -- the `google-genai` SDK supports caching on both the Gemini Developer API and Vertex AI backends. The existing `get_genai_client()` in `curation_service.py` already handles both backends via the `GOOGLE_GENAI_USE_VERTEXAI` flag.

Model routing is straightforward: each service constructor already accepts a `model` parameter, so routing can be implemented via a config-driven model resolver that maps node names to models. The review prompt is already well-structured with explicit criteria, making adaptive rubrics a matter of building content-type classifiers and criteria templates.

**Primary recommendation:** Implement model routing via a YAML config + resolver function; use explicit context caching for the review node's curated_topics/draft pair; build adaptive rubrics as content-type-keyed prompt templates.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-genai | 1.64.0 (already installed) | LLM calls, context caching API | Already in use; `client.caches` provides caching CRUD |
| pydantic | 2.12+ (already installed) | Config models, rubric schemas | Already in use for all models |
| pydantic-settings | 2.8+ (already installed) | Config loading | Already in use for Settings |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyYAML | latest | Model routing config files | For YAML-based node-model mapping config |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| YAML config for routing | JSON config | YAML more readable for humans, but JSON already used elsewhere; either works |
| Explicit caching | Implicit caching only | Implicit is automatic but opportunistic (no guaranteed savings); explicit gives control |

**Installation:**
```bash
uv add pyyaml
```

## Gemini Model Comparison (ADV-01)

### Pricing (per 1M tokens, Gemini Developer API, paid tier)

| Model | Input | Output | Cached Input | Context Window | Thinking |
|-------|-------|--------|-------------|----------------|----------|
| **Gemini 2.5 Pro** | $1.25 (<=200k), $2.50 (>200k) | $10.00 (<=200k), $15.00 (>200k) | $0.125/$0.25 | 1M tokens | Yes |
| **Gemini 2.5 Flash** | $0.30 (text) | $2.50 | $0.03 | 1M tokens | Yes (budget controllable) |
| **Gemini 2.5 Flash-Lite** | $0.10 (text) | $0.40 | N/A (check) | 1M tokens | No |

**Confidence:** HIGH -- verified via official Gemini API pricing page (ai.google.dev/pricing)

### Recommended Model Pool & Node Mapping

Based on task complexity analysis of each pipeline node:

| Node | Recommended Model | Rationale |
|------|-------------------|-----------|
| **curation** (research_trend) | Flash | Needs Google Search grounding; moderate complexity |
| **curation** (expand_subtopics) | Flash-Lite | Simple keyword extraction; low complexity |
| **curation** (extract_topic) | Flash-Lite | JSON extraction from text; structured output |
| **design_spec** | Flash-Lite | Simple structured JSON generation |
| **source** | N/A | No LLM calls (DB queries only) |
| **editorial** (content gen) | Flash | Complex creative writing; needs quality |
| **editorial** (image gen) | Flash-preview-image | Already separate; image generation model |
| **editorial** (layout parse) | Flash-Lite | Vision parsing to JSON; simple extraction |
| **editorial** (repair) | Flash-Lite | JSON repair; deterministic |
| **enrich** (keyword expand) | Flash-Lite | Simple keyword list generation |
| **enrich** (regenerate) | Flash | Creative re-writing with context; needs quality |
| **review** (LLM-as-Judge) | Flash | Critical evaluation; needs reasoning quality |

**Upgrade conditions (routing to higher-tier model):**
- Retry attempts (revision_count > 0): upgrade editorial from Flash to Pro
- Long input (>50K tokens): stay on Flash (Pro has no advantage at this range)
- Review failure after 2 attempts: upgrade review to Pro for deeper analysis

**Cost estimate per pipeline run (rough):**
- Current (all Flash): ~$0.02-0.05 per run
- Optimized (Flash + Flash-Lite mix): ~$0.01-0.03 per run
- With Pro upgrades on retry: ~$0.05-0.15 per retry run

## Context Caching Analysis (ADV-02)

### How Context Caching Works

The `google-genai` SDK provides `client.caches.create()` for explicit caching and automatic implicit caching.

**Explicit caching:**
```python
from google import genai
from google.genai import types

cache = client.caches.create(
    model='gemini-2.5-flash',
    config=types.CreateCachedContentConfig(
        contents=[types.Content(role='user', parts=[...])],
        system_instruction='...',
        display_name='editorial-source-cache',
        ttl='3600s',  # 1 hour
    )
)

# Use in generation
response = await client.aio.models.generate_content(
    model='gemini-2.5-flash',
    contents='User query here',
    config=types.GenerateContentConfig(cached_content=cache.name)
)
```

**Confidence:** HIGH -- verified via official docs and deepwiki SDK analysis

### Minimum Token Requirements
- Gemini 2.5 Flash: 1,024 tokens minimum
- Gemini 2.5 Pro: 2,048 tokens minimum (may be 4,096 per Vertex docs)
- Gemini 2.5 Flash-Lite: 2,048 tokens minimum

**Confidence:** MEDIUM -- official sources give slightly different numbers; 2,048 is the safe minimum for 2.5 models

### Caching Pricing
- Cached token reads: 90% discount on Gemini 2.5+ models (i.e., 10% of standard input cost)
- Storage: $4.50/1M tokens/hour (Pro), $1.00/1M tokens/hour (Flash)
- Cache creation: billed at standard input token rate

**Confidence:** HIGH -- from official pricing page

### Pipeline Caching Opportunities

Analysis of the codebase reveals these patterns where caching would help:

| Opportunity | What Gets Cached | When Reused | Token Estimate | Benefit |
|-------------|-----------------|-------------|----------------|---------|
| **Review prompt template + curated_topics** | The review system prompt + curated_topics JSON (ground truth) | On every retry (review fails -> editorial revises -> review again). Same curated_topics used 1-3 times. | 2K-10K tokens | Medium; saves on retry runs |
| **Editorial feedback-aware re-gen** | The trend_context + enriched_contexts (DB data) | On editorial retries; same source data, different draft. | 5K-20K tokens | Medium-High; large context repeated |
| **Curation DB context** | The `_build_db_context()` output | Changes infrequently (DB data updates slowly). Multiple curate_topic calls within a single curate_seed() use similar context. | 1K-3K tokens | Low; below minimum threshold usually |
| **System instructions** | Common system instructions across calls | Within a pipeline run | Varies | Low; implicit caching may handle this |

**Primary caching recommendation:**
1. **Review node**: Cache curated_topics as system context for review LLM calls. On retries, only the draft changes while curated_topics stays constant.
2. **Editorial node on retry**: Cache the trend_context + enriched_contexts. On retries (after review failure), only the feedback/draft changes.
3. **Implicit caching** is already available on Gemini 2.5 Flash -- it automatically caches common prefixes. Place static content (system instructions, curated data) at the beginning of prompts to maximize implicit cache hits.

### No SDK Migration Needed

**Critical finding:** The project already uses `google-genai` SDK (v1.64.0) which fully supports context caching via `client.caches`. No migration from `google-genai` to any other SDK is needed.

The `get_genai_client()` function in `curation_service.py` already supports both Gemini Developer API and Vertex AI backends. Context caching works on both.

**Confidence:** HIGH -- verified from codebase + official docs

### Cache Lifecycle Management

**Recommended policy:**
- TTL: 3600s (1 hour) for within-pipeline-run caches -- a single pipeline run typically completes within 5-15 minutes including retries
- Cache naming: `editorial-{thread_id}-{cache_type}` (e.g., `editorial-abc123-curated-topics`)
- Cleanup: Let TTL expire naturally; no explicit deletion needed for short-lived caches
- Cost tracking: Log `cached_content_token_count` from `response.usage_metadata` in observability collector

## Architecture Patterns

### Recommended Project Structure (new/modified files)

```
src/editorial_ai/
  config.py                    # Add model routing settings
  routing/
    __init__.py
    model_router.py            # Model selection logic
    routing_config.yaml        # Node-model mapping config
  rubrics/
    __init__.py
    classifier.py              # Content type classifier
    rubric_registry.py         # Rubric templates by content type
    templates/
      tech_blog.py             # Tech blog evaluation criteria
      fashion_magazine.py      # Fashion magazine evaluation criteria
      default.py               # Default/fallback criteria
  caching/
    __init__.py
    cache_manager.py           # Explicit cache create/use/cleanup
  services/
    review_service.py          # Modify to accept rubric config
    editorial_service.py       # Modify to use model router
    curation_service.py        # Modify to use model router
```

### Pattern 1: Config-Driven Model Router
**What:** A resolver function that maps (node_name, context) -> model_name
**When to use:** Every LLM call in the pipeline

```python
# Source: architecture design based on codebase analysis
import yaml
from dataclasses import dataclass

@dataclass
class ModelRoute:
    default_model: str
    upgrade_model: str | None = None
    upgrade_conditions: dict | None = None

class ModelRouter:
    def __init__(self, config_path: str = "routing_config.yaml"):
        with open(config_path) as f:
            self._config = yaml.safe_load(f)
        self._routes: dict[str, ModelRoute] = {}
        for node, cfg in self._config.get("nodes", {}).items():
            self._routes[node] = ModelRoute(
                default_model=cfg["default_model"],
                upgrade_model=cfg.get("upgrade_model"),
                upgrade_conditions=cfg.get("upgrade_conditions"),
            )

    def resolve(
        self,
        node_name: str,
        *,
        revision_count: int = 0,
        input_tokens: int = 0,
    ) -> str:
        route = self._routes.get(node_name)
        if not route:
            return "gemini-2.5-flash"  # safe default

        # Check upgrade conditions
        if route.upgrade_model and route.upgrade_conditions:
            conditions = route.upgrade_conditions
            if revision_count >= conditions.get("min_revision_count", 999):
                return route.upgrade_model
            if input_tokens >= conditions.get("min_input_tokens", 999999):
                return route.upgrade_model

        return route.default_model
```

### Pattern 2: Explicit Cache Manager
**What:** Wraps `client.caches` for pipeline-scoped caching with automatic TTL
**When to use:** When same context data is passed to multiple LLM calls

```python
# Source: based on google-genai SDK docs
from google import genai
from google.genai import types

class CacheManager:
    def __init__(self, client: genai.Client):
        self._client = client
        self._active_caches: dict[str, str] = {}  # key -> cache.name

    async def get_or_create(
        self,
        cache_key: str,
        model: str,
        contents: list[types.Content],
        *,
        system_instruction: str | None = None,
        ttl: str = "3600s",
    ) -> str:
        """Return cache name, creating if needed."""
        if cache_key in self._active_caches:
            try:
                # Verify cache still exists
                self._client.caches.get(name=self._active_caches[cache_key])
                return self._active_caches[cache_key]
            except Exception:
                del self._active_caches[cache_key]

        cache = await self._client.aio.caches.create(
            model=model,
            config=types.CreateCachedContentConfig(
                contents=contents,
                system_instruction=system_instruction,
                display_name=cache_key,
                ttl=ttl,
            )
        )
        self._active_caches[cache_key] = cache.name
        return cache.name
```

### Pattern 3: Adaptive Rubric Registry
**What:** Content-type-specific evaluation criteria for the review node
**When to use:** At review node entry, after classifying content type

```python
# Source: architecture design
from enum import Enum

class ContentType(str, Enum):
    TECH_BLOG = "tech_blog"
    FASHION_MAGAZINE = "fashion_magazine"
    LIFESTYLE = "lifestyle"
    DEFAULT = "default"

@dataclass
class RubricConfig:
    content_type: ContentType
    criteria_weights: dict[str, float]  # criterion -> weight
    extra_criteria: list[str]
    prompt_additions: str  # extra instructions for review prompt

RUBRIC_REGISTRY: dict[ContentType, RubricConfig] = {
    ContentType.FASHION_MAGAZINE: RubricConfig(
        content_type=ContentType.FASHION_MAGAZINE,
        criteria_weights={
            "hallucination": 1.0,
            "fact_accuracy": 1.0,
            "content_completeness": 1.0,
            "visual_appeal": 0.8,   # fashion-specific
            "trend_relevance": 0.9, # fashion-specific
        },
        extra_criteria=["visual_appeal", "trend_relevance"],
        prompt_additions="패션 트렌드 정확성과 시각적 표현력을 특히 중점 평가하세요.",
    ),
    ContentType.TECH_BLOG: RubricConfig(
        content_type=ContentType.TECH_BLOG,
        criteria_weights={
            "hallucination": 1.0,
            "fact_accuracy": 1.2,    # higher weight for tech accuracy
            "content_completeness": 1.0,
            "technical_depth": 0.9,  # tech-specific
        },
        extra_criteria=["technical_depth"],
        prompt_additions="기술 용어의 정확성과 설명 깊이를 특히 중점 평가하세요.",
    ),
}
```

### Anti-Patterns to Avoid
- **Hard-coding model names in services:** Every service already has `model` params -- use the router, don't scatter model names
- **Caching everything:** Only cache when token savings exceed cache creation + storage cost. Below 2K tokens, implicit caching is sufficient
- **Complex content classifiers:** Start with keyword-based classification (the `curation_input` already has a keyword domain). Don't build an ML classifier

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cache TTL management | Custom expiry tracking | `google-genai` cache TTL (`ttl` param) | SDK handles expiry automatically |
| Token counting for cache threshold | Manual tokenizer | `response.usage_metadata.cached_content_token_count` | SDK reports cache hits; check after first call |
| Model availability checking | Custom health checks | Existing `retry_on_api_error` with `tenacity` | Already handles API errors with retry |
| Prompt prefix optimization for implicit caching | Custom prompt reordering | Structure prompts with static prefix | Just put system instructions + context first |

**Key insight:** The `google-genai` SDK already handles most caching complexity. The main engineering work is deciding *what* to cache and *where* to route, not building cache infrastructure.

## Common Pitfalls

### Pitfall 1: Caching Content Below Minimum Token Threshold
**What goes wrong:** Creating caches with <1024 tokens (Flash) or <2048 tokens (Pro) silently fails or wastes API calls
**Why it happens:** Short prompts like keyword expansion or design spec generation have small inputs
**How to avoid:** Only apply explicit caching to nodes with >2K input tokens. Use token estimation before cache creation.
**Warning signs:** `cached_content_token_count` always 0 in usage metadata

### Pitfall 2: Cache Storage Costs Exceeding Savings
**What goes wrong:** Creating many long-lived caches costs more in storage than saved on input tokens
**Why it happens:** Storage is billed per hour per token; a 10K token cache at $1.00/1M/hr costs $0.01/hr for Flash
**How to avoid:** Use short TTLs (1 hour max for pipeline-scoped caches). Only cache when expected reuse > 2 times.
**Warning signs:** Storage cost on GCP billing exceeds input token savings

### Pitfall 3: Model Routing Breaking Structured Output
**What goes wrong:** Switching from Flash to Flash-Lite breaks `response_schema` structured output
**Why it happens:** Different models may have different structured output capabilities
**How to avoid:** Test all model routes with the actual prompts and response_schema. Flash-Lite supports structured output, but validate.
**Warning signs:** Increased parse failures after enabling routing

### Pitfall 4: Cache Invalidation on Curated Data Changes
**What goes wrong:** Stale curated_topics cached from a previous run used in current review
**Why it happens:** If thread_id-based cache key collides or TTL too long
**How to avoid:** Include a hash of cached content in the cache key. Use short TTLs. Scope caches to pipeline run, not globally.
**Warning signs:** Review passes with outdated ground truth

### Pitfall 5: Adaptive Rubric Over-Engineering
**What goes wrong:** Building complex NLP classifiers for content type when simple rules suffice
**Why it happens:** Temptation to "do it right" from the start
**How to avoid:** Start with keyword-domain classification from `curation_input`. The pipeline already has a `keyword` field that indicates content domain.
**Warning signs:** Spending more time on classifier than on actual rubric criteria

## Code Examples

### Model Routing Config (YAML)
```yaml
# routing_config.yaml
defaults:
  model: "gemini-2.5-flash"
  temperature: 0.7

nodes:
  curation_research:
    default_model: "gemini-2.5-flash"
    # Needs Google Search grounding, moderate complexity
  curation_subtopics:
    default_model: "gemini-2.5-flash-lite"
  curation_extract:
    default_model: "gemini-2.5-flash-lite"
  design_spec:
    default_model: "gemini-2.5-flash-lite"
  editorial_content:
    default_model: "gemini-2.5-flash"
    upgrade_model: "gemini-2.5-pro"
    upgrade_conditions:
      min_revision_count: 2  # upgrade on 3rd attempt
  editorial_layout_parse:
    default_model: "gemini-2.5-flash-lite"
  editorial_repair:
    default_model: "gemini-2.5-flash-lite"
  enrich_keywords:
    default_model: "gemini-2.5-flash-lite"
  enrich_regenerate:
    default_model: "gemini-2.5-flash"
  review:
    default_model: "gemini-2.5-flash"
    upgrade_model: "gemini-2.5-pro"
    upgrade_conditions:
      min_revision_count: 2
```

### Using Cache in Review Service
```python
# Modified review_service.py
async def evaluate_with_llm(
    self,
    draft_json: str,
    curated_topics_json: str,
    *,
    cache_name: str | None = None,
) -> list[CriterionResult]:
    prompt = build_review_prompt(draft_json, curated_topics_json)

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ReviewResult,
        temperature=0.0,
    )
    if cache_name:
        config.cached_content = cache_name

    response = await self.client.aio.models.generate_content(
        model=self.model,
        contents=prompt,
        config=config,
    )
    # ...
```

### Content Type Classifier (Keyword-Based)
```python
# rubrics/classifier.py
KEYWORD_DOMAIN_MAP: dict[str, ContentType] = {
    # Tech keywords
    "AI": ContentType.TECH_BLOG,
    "tech": ContentType.TECH_BLOG,
    "developer": ContentType.TECH_BLOG,
    "coding": ContentType.TECH_BLOG,
    # Fashion keywords (default for this pipeline)
    "fashion": ContentType.FASHION_MAGAZINE,
    "style": ContentType.FASHION_MAGAZINE,
    "trend": ContentType.FASHION_MAGAZINE,
    "runway": ContentType.FASHION_MAGAZINE,
}

def classify_content_type(keyword: str, curated_topics: list[dict]) -> ContentType:
    """Classify content type from seed keyword and curated topics."""
    # Check keyword against domain map
    keyword_lower = keyword.lower()
    for domain_keyword, content_type in KEYWORD_DOMAIN_MAP.items():
        if domain_keyword.lower() in keyword_lower:
            return content_type

    # Check related_keywords from curated topics
    for topic in curated_topics:
        for rk in topic.get("related_keywords", []):
            rk_lower = rk.lower()
            for domain_keyword, content_type in KEYWORD_DOMAIN_MAP.items():
                if domain_keyword.lower() in rk_lower:
                    return content_type

    return ContentType.FASHION_MAGAZINE  # default for this pipeline
```

### Logging Model Routing Decisions
```python
# In observability/collector.py (extend TokenUsage model)
class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0          # NEW: cached_content_token_count
    model_name: str | None = None
    routing_reason: str | None = None  # NEW: why this model was chosen
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single model for all tasks | Per-task model routing | Gemini 2.5 model family (2025) | 5-10x cost reduction on simple tasks |
| No caching | Implicit caching (auto) | May 2025 | Automatic 75-90% discount on repeated prefixes |
| Implicit only | Explicit + implicit caching | Gemini 2.5+ (2025) | Guaranteed savings with explicit; 90% discount |
| vertexai SDK | google-genai SDK | June 2025 migration | Unified SDK for both APIs; old vertexai deprecated |

**Deprecated/outdated:**
- `vertexai.generative_models` module: Deprecated June 2025, removal June 2026. Use `google-genai` SDK instead.
- `vertexai.caching`: Same deprecation timeline. Use `client.caches` from `google-genai`.

## Open Questions

1. **Flash-Lite context caching support**
   - What we know: Official docs list Flash-Lite for implicit caching. Explicit caching support is listed on Vertex AI docs.
   - What's unclear: Whether explicit caching works with Flash-Lite on Gemini Developer API (not listed on ai.google.dev caching page)
   - Recommendation: Use Flash for cached nodes, Flash-Lite only for non-cached simple tasks. Test explicitly.

2. **Actual token usage per node (for cost modeling)**
   - What we know: Observability logs token usage per node already
   - What's unclear: We haven't analyzed real pipeline run data to identify exact token counts per node
   - Recommendation: Analyze existing JSONL observability logs before implementing. First task should be a data analysis step to validate the model routing recommendations.

3. **Google Search grounding + context caching compatibility**
   - What we know: Curation node uses `tools=[types.Tool(google_search=types.GoogleSearch())]`
   - What's unclear: Whether explicit caching works alongside Google Search tool
   - Recommendation: Test explicitly. If incompatible, only apply caching to non-grounded calls.

4. **Structured output (response_schema) with Flash-Lite**
   - What we know: Flash-Lite supports `response_mime_type="application/json"` and `response_schema`
   - What's unclear: Quality/reliability differences between Flash and Flash-Lite for complex schemas
   - Recommendation: Test with actual pipeline schemas (EditorialContent, ReviewResult) before deploying

## Sources

### Primary (HIGH confidence)
- [Gemini API Pricing](https://ai.google.dev/pricing) -- model pricing, cached token pricing
- [Gemini API Context Caching docs](https://ai.google.dev/gemini-api/docs/caching) -- caching API, minimum tokens, code examples
- [Vertex AI Context Caching Overview](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/context-cache/context-cache-overview) -- supported models, minimum tokens, constraints
- [google-genai SDK caching API](https://deepwiki.com/googleapis/python-genai/10.1-content-caching) -- Python SDK API reference
- Codebase analysis -- `llm.py`, `curation_service.py`, `editorial_service.py`, `review_service.py`, `enrich_service.py`, `observability/collector.py`

### Secondary (MEDIUM confidence)
- [Gemini 2.5 Implicit Caching blog](https://developers.googleblog.com/en/gemini-2-5-models-now-support-implicit-caching/) -- implicit caching details, 75% discount
- [Gemini 2.5 Flash-Lite GA blog](https://developers.googleblog.com/en/gemini-25-flash-lite-is-now-stable-and-generally-available/) -- Flash-Lite capabilities
- [Vertex AI Create Cache docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/context-cache/context-cache-create) -- Vertex-specific creation examples

### Tertiary (LOW confidence)
- WebSearch results for Flash-Lite context caching -- conflicting information on explicit caching support
- Token cost estimates per pipeline run -- based on model pricing, not actual usage data

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies needed; google-genai already supports caching
- Model routing: HIGH -- pricing verified, architecture straightforward from existing code patterns
- Context caching: MEDIUM-HIGH -- API verified, but real-world benefit depends on actual token volumes (open question #2)
- Adaptive rubrics: MEDIUM -- architecture pattern is sound, but specific criteria/weights need tuning with real content
- Pitfalls: HIGH -- derived from official docs constraints and codebase analysis

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (30 days -- Gemini API stable, pricing may change)
