# Phase 6: Review Agent + Feedback Loop - Research

**Researched:** 2026-02-25
**Domain:** LLM-as-a-Judge evaluation, structured feedback loop, LangGraph conditional edge retry patterns
**Confidence:** HIGH

## Summary

Phase 6 implements an LLM-as-a-Judge review node that evaluates generated editorial drafts across four criteria (hallucination, format, fact accuracy, content completeness), produces structured feedback on failure, and wires a feedback loop back to the editorial node via the existing LangGraph conditional edge. The state schema already contains all necessary fields (`review_result`, `revision_count`, `feedback_history`), and the graph already has a `route_after_review` conditional edge with retry/escalation logic -- this phase replaces `stub_review` with a real implementation and modifies the editorial node to consume feedback.

The codebase follows a consistent 3-layer pattern: **prompts** (pure template functions) -> **service** (LLM orchestration + validation) -> **node** (thin state adapter). Phase 6 follows this same pattern: `prompts/review.py` for evaluation prompts, `services/review_service.py` for LLM-as-a-Judge logic + Pydantic schema validation, and `nodes/review.py` for the LangGraph node. Additionally, the editorial node and/or service must be modified to accept feedback from prior review failures.

The primary technical challenge is designing an evaluation prompt that reliably produces consistent pass/fail results with actionable feedback. The format criterion can be partially automated with Pydantic validation (schema compliance check) before the LLM evaluation, reducing LLM load and improving reliability.

**Primary recommendation:** Use a hybrid approach: Pydantic schema validation for format checks (deterministic, fast), LLM-as-a-Judge for hallucination, fact accuracy, and content completeness (require semantic understanding). Use per-criterion pass/fail with mandatory/optional distinction. Store evaluation results in `review_result` and append feedback to `feedback_history` (Annotated list with operator.add). Inject feedback into editorial regeneration via state field + prompt modification.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `google-genai` | 1.64.0 | LLM-as-a-Judge evaluation via Gemini structured output | Already installed; same SDK pattern as curation/editorial services |
| `pydantic` | 2.12.5 | Review result schema, format validation, feedback schema | Already installed; `model_validate()` for format check; structured output schema |
| `langgraph` | 1.0.9 | Conditional edge routing (already wired), state management | Graph topology already exists; replace stub with real node |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tenacity` | (transitive) | Retry on Gemini API errors during evaluation | Same `retry_on_api_error` decorator from curation_service |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single Gemini evaluation call | Separate LLM call per criterion | Per-criterion is more accurate but 4x API calls; single call is faster and cheaper; recommend single call with structured output for all 4 criteria |
| Gemini as evaluator | Different model (Claude, GPT-4) as evaluator | Different model adds API key management complexity; Gemini is already integrated and available; same-model evaluation is standard for LLM-as-a-Judge |
| LLM-only format check | Pydantic validation + LLM | Pydantic catches schema issues deterministically; LLM evaluation adds semantic format quality (e.g., "are block types appropriate for fashion editorial"); recommend hybrid |

**Installation:**
```bash
# No new dependencies needed -- all libraries already installed
```

## Architecture Patterns

### Recommended Project Structure
```
src/editorial_ai/
├── models/
│   └── review.py            # ReviewResult, CriterionResult Pydantic models
├── nodes/
│   └── review.py            # LangGraph review node (replaces stub_review)
├── services/
│   └── review_service.py    # LLM-as-a-Judge evaluation logic
├── prompts/
│   └── review.py            # Evaluation prompt templates
├── nodes/
│   └── editorial.py         # MODIFY: accept feedback_history for regeneration
├── services/
│   └── editorial_service.py # MODIFY: accept feedback parameter
└── prompts/
    └── editorial.py         # MODIFY: add feedback injection prompt builder
```

### Pattern 1: Review Result Schema (Pydantic Structured Output)
**What:** Define Pydantic models for the LLM-as-a-Judge evaluation output. Each criterion has a pass/fail result with a reason. The overall result aggregates all criteria.
**When to use:** Every review evaluation call.
**Example:**
```python
# models/review.py
from pydantic import BaseModel, Field
from typing import Literal

class CriterionResult(BaseModel):
    """Result for a single evaluation criterion."""
    criterion: Literal["hallucination", "format", "fact_accuracy", "content_completeness"]
    passed: bool
    reason: str  # Why it passed or failed -- actionable feedback
    severity: Literal["critical", "major", "minor"] = "major"

class ReviewResult(BaseModel):
    """Complete review evaluation result."""
    passed: bool  # Overall pass/fail
    criteria: list[CriterionResult]
    summary: str  # Brief overall assessment
    suggestions: list[str] = Field(default_factory=list)  # Improvement suggestions
```

### Pattern 2: Hybrid Evaluation (Pydantic + LLM)
**What:** Run deterministic Pydantic schema validation first (format check), then LLM evaluation for semantic criteria. This reduces LLM burden and provides fast-fail for structural issues.
**When to use:** Every review pass. Format validation should run before LLM evaluation.
**Example:**
```python
# services/review_service.py
from editorial_ai.models.layout import MagazineLayout

def validate_format(draft: dict) -> CriterionResult:
    """Deterministic format validation using Pydantic."""
    try:
        layout = MagazineLayout.model_validate(draft)
        # Additional structural checks
        has_hero = any(b.type == "hero" for b in layout.blocks)
        has_body = any(b.type == "body_text" for b in layout.blocks)
        if not has_hero or not has_body:
            return CriterionResult(
                criterion="format",
                passed=False,
                reason="Missing required block types: hero and body_text are mandatory",
                severity="critical",
            )
        return CriterionResult(criterion="format", passed=True, reason="Schema valid, required blocks present")
    except ValidationError as e:
        return CriterionResult(
            criterion="format",
            passed=False,
            reason=f"Schema validation failed: {e}",
            severity="critical",
        )
```

### Pattern 3: LLM-as-a-Judge Evaluation Prompt
**What:** Send the draft content + evaluation criteria to Gemini with structured output for consistent scoring. Include the original input context (curated_topics) to enable fact-checking against source material.
**When to use:** After format validation passes or alongside format validation.
**Example:**
```python
# prompts/review.py
def build_review_prompt(draft_json: str, curated_topics_json: str) -> str:
    return f"""당신은 패션 매거진 편집장입니다. 다음 에디토리얼 초안을 품질 평가해주세요.

에디토리얼 초안 (Layout JSON):
{draft_json}

원본 큐레이션 데이터 (팩트 검증 참고):
{curated_topics_json}

다음 기준으로 평가하세요:

1. **hallucination** (할루시네이션): 초안에 큐레이션 데이터에 없는 허위 정보가 포함되어 있는지
   - 존재하지 않는 브랜드, 셀럽, 이벤트 등을 확인
   - 실제 존재하는 정보라도 큐레이션 맥락과 관련 없는 정보는 할루시네이션으로 간주

2. **fact_accuracy** (팩트 정확성): 언급된 정보가 큐레이션 데이터와 일치하는지
   - 브랜드명, 셀럽명, 트렌드 설명의 정확성
   - 날짜, 이벤트, 시즌 정보의 일치 여부

3. **content_completeness** (컨텐츠 완성도): 에디토리얼로서 충분한 내용이 포함되었는지
   - 셀럽/인플루언서 참조가 1개 이상 포함
   - 상품/브랜드 참조가 1개 이상 포함
   - 본문이 2개 이상의 단락으로 구성
   - 해시태그가 포함

각 기준별로 passed(통과/실패), reason(구체적 사유), severity(critical/major/minor)를 평가하세요.
전체 통과 여부(passed)와 요약(summary), 개선 제안(suggestions)도 포함하세요.

반드시 유효한 JSON만 출력하세요."""
```

### Pattern 4: Feedback Injection into Editorial Regeneration
**What:** When review fails and the graph routes back to editorial, the editorial node reads `feedback_history` from state and injects it into the content generation prompt. This prevents the same mistakes from repeating.
**When to use:** On retry iterations (revision_count > 0).
**Example:**
```python
# prompts/editorial.py (modification)
def build_content_generation_prompt_with_feedback(
    keyword: str,
    trend_context: str,
    feedback_history: list[dict],
    previous_draft: dict | None = None,
) -> str:
    base_prompt = build_content_generation_prompt(keyword, trend_context)

    if not feedback_history:
        return base_prompt

    feedback_section = "\n\n--- 이전 검수 피드백 (반드시 반영하세요) ---\n"
    for i, feedback in enumerate(feedback_history, 1):
        feedback_section += f"\n[시도 {i}]\n"
        for criterion in feedback.get("criteria", []):
            if not criterion.get("passed"):
                feedback_section += f"- {criterion['criterion']}: {criterion['reason']}\n"
        if feedback.get("suggestions"):
            feedback_section += f"개선 제안: {', '.join(feedback['suggestions'])}\n"

    if previous_draft:
        feedback_section += f"\n이전 초안 제목: {previous_draft.get('title', 'N/A')}\n"
        feedback_section += "위 피드백을 반영하여 개선된 새로운 초안을 작성하세요.\n"

    return base_prompt + feedback_section
```

### Pattern 5: Review Node State Management
**What:** The review node writes `review_result`, increments `revision_count` on failure, and appends to `feedback_history`. The existing `route_after_review` function already handles routing based on `review_result.passed` and `revision_count >= 3`.
**When to use:** Every review node execution.
**Example:**
```python
# nodes/review.py
async def review_node(state: EditorialPipelineState) -> dict:
    current_draft = state.get("current_draft")
    if not current_draft:
        return {
            "pipeline_status": "failed",
            "review_result": {"passed": False},
            "error_log": ["Review failed: no current_draft in state"],
        }

    curated_topics = state.get("curated_topics") or []
    service = ReviewService(get_genai_client())
    result = await service.evaluate(current_draft, curated_topics)

    update: dict = {
        "review_result": result.model_dump(),
    }

    if result.passed:
        update["pipeline_status"] = "awaiting_approval"
    else:
        update["revision_count"] = state.get("revision_count", 0) + 1
        update["feedback_history"] = [result.model_dump()]  # appended via operator.add
        # pipeline_status stays "reviewing" -- route_after_review handles routing

    return update
```

### Anti-Patterns to Avoid
- **Scoring without actionable feedback:** A numeric score alone (e.g., 7/10) does not help the editorial agent improve. Each failed criterion must include a specific, actionable reason.
- **Evaluating layout-only without source context:** Without the original curated_topics, the evaluator cannot check hallucination or fact accuracy. Always include source material in the evaluation context.
- **Modifying `route_after_review` for this phase:** The conditional edge logic already works correctly. The review node just needs to produce state updates that the existing routing function understands.
- **Re-running enrich on feedback loop:** When review routes back to editorial, the flow should be `editorial -> enrich -> review` (the existing graph edge). Do NOT add a direct `review -> editorial` edge that bypasses enrich -- the current `editorial -> enrich -> review` chain handles this correctly since `route_after_review` returns `"editorial"` which triggers the full `editorial -> enrich -> review` path.
- **Storing raw LLM evaluation text instead of structured result:** Always parse evaluation into the ReviewResult Pydantic model for consistent downstream processing.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema validation | Custom recursive validator | `MagazineLayout.model_validate(draft)` | Pydantic already handles all layout validation; catches missing fields, wrong types, invalid enum values |
| Retry counter logic | Custom counter in review node | Existing `revision_count` state field + `route_after_review` | Graph topology already handles max retry routing; review node just increments the counter |
| Feedback accumulation | Custom list management | `feedback_history: Annotated[list[dict], operator.add]` | State schema already uses operator.add reducer for list append -- just return a single-item list |
| API retry with backoff | Custom sleep loops | `retry_on_api_error` from curation_service | Same tenacity decorator used across all services |
| Conditional routing | Custom routing in review node | `route_after_review` in graph.py | Already implemented and tested (test_graph.py has happy path, retry, and max retry tests) |

**Key insight:** The graph skeleton (Phase 1) already anticipated this phase. State fields, conditional edges, and routing logic are all in place. Phase 6 is primarily about implementing the review service/node and modifying the editorial node to accept feedback -- not about graph topology changes.

## Common Pitfalls

### Pitfall 1: LLM-as-a-Judge Inconsistency
**What goes wrong:** The same draft receives different pass/fail results across multiple evaluation runs. Hallucination detection is especially prone to inconsistency.
**Why it happens:** LLM evaluation is inherently stochastic. Even with temperature=0, token sampling can vary.
**How to avoid:** (1) Use `temperature=0.0` for deterministic evaluation. (2) Use Gemini structured output (`response_schema=ReviewResult`) to constrain output format. (3) Make evaluation criteria as specific as possible in the prompt. (4) Use Pydantic validation for the format criterion (deterministic).
**Warning signs:** Tests that check review results intermittently fail; same content passes review on retry without changes.

### Pitfall 2: Feedback Loop Does Not Improve Output
**What goes wrong:** The editorial agent receives feedback but regenerates content with the same issues. The retry loop exhausts all attempts without improvement.
**Why it happens:** Feedback is too vague (e.g., "content is incomplete"), or the editorial prompt does not strongly emphasize the feedback, or the feedback is injected in a way the LLM ignores.
**How to avoid:** (1) Make feedback criterion-specific and actionable: "Missing celeb references -- include at least 1 celebrity from the curated data." (2) Place feedback prominently in the prompt (before the main instruction, not as a footnote). (3) Include the previous draft summary so the LLM understands what to change. (4) Consider including the failing criterion's severity to signal priority.
**Warning signs:** `revision_count` consistently reaches max (3) without passing review; regenerated content is near-identical to original.

### Pitfall 3: Escalation Without Useful Context
**What goes wrong:** After 3 failed retries, the pipeline terminates (routes to END) but the operator has no visibility into why.
**Why it happens:** The current `route_after_review` routes to END on max retries, but doesn't set a meaningful pipeline_status or preserve the failure context.
**How to avoid:** (1) Set `pipeline_status = "failed"` when max retries are hit (currently the review node doesn't distinguish this). (2) The accumulated `feedback_history` preserves all failure reasons. (3) Consider updating `route_after_review` or the review node to set a specific escalation status. (4) `error_log` should receive an escalation message.
**Warning signs:** Pipeline ends with `pipeline_status = "reviewing"` instead of a clear terminal state.

### Pitfall 4: Review Node Evaluates Empty/Invalid Draft
**What goes wrong:** The editorial node fails silently (returns `current_draft: None`), and the review node tries to evaluate a null draft.
**Why it happens:** The enrich node passes through on failure (returns `error_log` only, no `current_draft` update). If editorial fails, `current_draft` stays None.
**How to avoid:** (1) Check `current_draft is not None` at the start of review node. (2) Return immediate failure if no draft exists. (3) The editorial node already sets `pipeline_status = "failed"` on error, but the graph flow still continues to enrich -> review.
**Warning signs:** Review node receives null state; evaluation LLM call fails with empty input.

### Pitfall 5: Feedback History Grows Unbounded in State
**What goes wrong:** Each retry appends a full ReviewResult dict to `feedback_history`. With 3 retries, state grows significantly.
**Why it happens:** `operator.add` accumulates across all retries. ReviewResult includes full criteria details + suggestions.
**How to avoid:** (1) Keep feedback entries concise -- only include failed criteria and key suggestions, not the full ReviewResult. (2) 3 retries maximum means at most 3 entries -- this is manageable. (3) Consider trimming when injecting into the editorial prompt (use only the latest feedback or summarize).
**Warning signs:** State serialization becomes slow; editorial prompt exceeds token limit due to accumulated feedback.

### Pitfall 6: Enrich Node Re-runs on Every Retry Loop
**What goes wrong:** When review fails and routes back to editorial, the flow is `editorial -> enrich -> review`. The enrich node makes Supabase + Gemini calls every time, which is slow and potentially gives different results.
**Why it happens:** The graph edge `editorial -> enrich -> review` is fixed -- there is no bypass for retries.
**How to avoid:** This is actually acceptable behavior because (1) the editorial node regenerates content that may reference different celebs/products, so enrichment should re-run, and (2) the enrich node has graceful passthrough (returns original if no DB results). However, be aware of the latency impact. If this becomes a bottleneck, consider making enrich conditional based on revision_count, but this is a premature optimization for Phase 6.
**Warning signs:** Pipeline takes >60 seconds per retry due to repeated enrichment.

## Code Examples

### Complete Review Service
```python
# Source: project pattern from curation_service.py, editorial_service.py
from google import genai
from google.genai import types
from pydantic import ValidationError

from editorial_ai.config import settings
from editorial_ai.models.layout import MagazineLayout
from editorial_ai.models.review import CriterionResult, ReviewResult
from editorial_ai.prompts.review import build_review_prompt
from editorial_ai.services.curation_service import (
    _strip_markdown_fences,
    get_genai_client,
    retry_on_api_error,
)

class ReviewService:
    def __init__(self, client: genai.Client, *, model: str | None = None):
        self.client = client
        self.model = model or settings.default_model

    def validate_format(self, draft: dict) -> CriterionResult:
        """Deterministic format validation via Pydantic."""
        try:
            layout = MagazineLayout.model_validate(draft)
            # Structural checks
            block_types = {b.type for b in layout.blocks}  # type: ignore[union-attr]
            issues = []
            if "body_text" not in block_types:
                issues.append("body_text block missing")
            if not layout.title:
                issues.append("title is empty")
            if issues:
                return CriterionResult(
                    criterion="format",
                    passed=False,
                    reason=f"Structural issues: {'; '.join(issues)}",
                    severity="critical",
                )
            return CriterionResult(
                criterion="format", passed=True, reason="Schema valid, structure complete"
            )
        except ValidationError as e:
            return CriterionResult(
                criterion="format",
                passed=False,
                reason=f"Schema validation failed: {e}",
                severity="critical",
            )

    @retry_on_api_error
    async def evaluate_with_llm(
        self, draft_json: str, curated_topics_json: str
    ) -> list[CriterionResult]:
        """LLM-as-a-Judge for hallucination, fact accuracy, content completeness."""
        prompt = build_review_prompt(draft_json, curated_topics_json)
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReviewResult,
                temperature=0.0,
            ),
        )
        raw_text = response.text or "{}"
        result = ReviewResult.model_validate_json(_strip_markdown_fences(raw_text))
        return result.criteria

    async def evaluate(
        self, draft: dict, curated_topics: list[dict]
    ) -> ReviewResult:
        """Full evaluation: format (Pydantic) + LLM (semantic)."""
        import json

        # Step 1: Deterministic format check
        format_result = self.validate_format(draft)

        # Step 2: LLM evaluation for semantic criteria
        draft_json = json.dumps(draft, ensure_ascii=False)
        topics_json = json.dumps(curated_topics, ensure_ascii=False)
        llm_criteria = await self.evaluate_with_llm(draft_json, topics_json)

        # Combine: replace any LLM format criterion with deterministic result
        all_criteria = [format_result]
        for c in llm_criteria:
            if c.criterion != "format":
                all_criteria.append(c)

        # Overall pass: all critical criteria must pass
        critical_failed = any(
            not c.passed and c.severity == "critical" for c in all_criteria
        )
        all_passed = all(c.passed for c in all_criteria)
        overall_passed = not critical_failed and all_passed

        return ReviewResult(
            passed=overall_passed,
            criteria=all_criteria,
            summary="All criteria passed" if overall_passed else "Review failed",
            suggestions=[c.reason for c in all_criteria if not c.passed],
        )
```

### Review Node (LangGraph)
```python
# Source: project node pattern from editorial.py, enrich.py
from editorial_ai.services.review_service import ReviewService
from editorial_ai.services.curation_service import get_genai_client
from editorial_ai.state import EditorialPipelineState

async def review_node(state: EditorialPipelineState) -> dict:
    current_draft = state.get("current_draft")
    if not current_draft:
        return {
            "review_result": {"passed": False},
            "revision_count": state.get("revision_count", 0) + 1,
            "feedback_history": [{"criteria": [], "summary": "No draft to review"}],
            "error_log": ["Review skipped: no current_draft in state"],
        }

    curated_topics = state.get("curated_topics") or []
    service = ReviewService(get_genai_client())
    result = await service.evaluate(current_draft, curated_topics)
    result_dict = result.model_dump()

    update: dict = {"review_result": result_dict}

    if result.passed:
        update["pipeline_status"] = "awaiting_approval"
    else:
        update["revision_count"] = state.get("revision_count", 0) + 1
        update["feedback_history"] = [result_dict]

    return update
```

### Editorial Node Feedback Injection
```python
# Modification to existing editorial_node in nodes/editorial.py
async def editorial_node(state: EditorialPipelineState) -> dict:
    curated_topics = state.get("curated_topics") or []
    feedback_history = state.get("feedback_history") or []
    previous_draft = state.get("current_draft")

    # ... existing validation ...

    # Use feedback-aware prompt if retrying
    if feedback_history:
        prompt = build_content_generation_prompt_with_feedback(
            primary_keyword, trend_context, feedback_history, previous_draft
        )
    else:
        prompt = build_content_generation_prompt(primary_keyword, trend_context)

    # ... rest of generation logic using the appropriate prompt ...
```

## Existing Infrastructure Analysis

### State Schema (Already Complete)
The `EditorialPipelineState` already has all fields needed for Phase 6:
- `review_result: dict | None` -- stores the ReviewResult
- `revision_count: int` -- tracks retry attempts
- `feedback_history: Annotated[list[dict], operator.add]` -- accumulates feedback across retries

### Graph Topology (Already Wired)
The `route_after_review` function in `graph.py` already implements the correct logic:
- `review_result.passed == True` -> routes to `"admin_gate"`
- `revision_count >= 3` -> routes to `END` (escalation)
- Otherwise -> routes to `"editorial"` (retry)

The conditional edge is already registered:
```python
builder.add_conditional_edges("review", route_after_review, ["admin_gate", "editorial", END])
```

### Existing Tests (Already Cover Routing)
`test_graph.py` already tests:
- Happy path (review passes -> admin_gate -> publish)
- Review fail then pass (retry succeeds)
- Max retries (revision_count >= 3 -> terminates)

### What Needs to Change
1. **New files:** `models/review.py`, `services/review_service.py`, `prompts/review.py`, `nodes/review.py`
2. **Modified files:** `nodes/editorial.py` (feedback injection), `prompts/editorial.py` (feedback prompt builder), `graph.py` (import real review_node instead of stub), `models/__init__.py` (export new models)
3. **Potentially modified:** `route_after_review` in `graph.py` -- consider setting `pipeline_status = "failed"` on escalation (currently the review node should handle this)

## Design Recommendations (Claude's Discretion Items)

### Evaluation Criteria Weights/Importance
**Recommendation:** Use mandatory/optional distinction instead of numeric weights.
- **Mandatory (must pass):** format (critical severity), hallucination (critical)
- **Important (should pass):** fact_accuracy (major severity), content_completeness (major)
- **Overall pass rule:** All mandatory criteria must pass AND at least one important criterion must pass. This prevents overly strict evaluation while ensuring structural and factual integrity.

### Evaluation Result Format
**Recommendation:** Per-criterion pass/fail with severity levels (critical/major/minor). NOT numeric scores.
- Rationale: Pass/fail is directly actionable for routing decisions. Numeric scores require arbitrary thresholds and are harder to generate consistently with LLMs. Severity levels allow nuanced handling (critical = must fix, major = should fix, minor = nice to fix).

### Validation Scope
**Recommendation:** Hybrid -- Pydantic schema validation for format + LLM for semantic criteria.
- Format check via `MagazineLayout.model_validate()` is deterministic, fast, and free.
- LLM evaluation handles hallucination, facts, and completeness which require semantic understanding.
- This reduces the LLM's burden and ensures format never has false negatives.

### Evaluation Context Scope
**Recommendation:** Include both Layout JSON AND curated_topics in the evaluation prompt.
- Layout JSON alone cannot verify hallucination or fact accuracy -- the evaluator needs the source material.
- Curated topics provide the ground truth for fact checking.
- Do NOT include `enriched_contexts` (not populated in current pipeline) or `curation_input` (too sparse).

### Evaluation LLM Model
**Recommendation:** Use the same Gemini model (`settings.default_model`, currently `gemini-2.5-flash`).
- Same SDK, same authentication, no additional setup.
- Use `temperature=0.0` for consistency (evaluation should be deterministic).
- The review service should accept an optional model override via constructor for future flexibility.

### Evaluation Results Storage
**Recommendation:** Store in GraphState via existing fields.
- `review_result` gets the full ReviewResult dict (latest evaluation only).
- `feedback_history` accumulates across retries via `operator.add`.
- No additional Supabase storage needed in Phase 6 (Phase 7 handles persistence).

### Feedback Delivery Method
**Recommendation:** State field + prompt injection.
- Feedback flows through `feedback_history` state field (already defined with operator.add).
- Editorial node reads `feedback_history` from state and injects into generation prompt.
- Include the previous draft's title/summary (not full content) for context.
- Place feedback BEFORE the main generation instructions for maximum LLM attention.

### Previous Draft Inclusion
**Recommendation:** Include summary only (title + failed criteria), not the full draft.
- Full draft in prompt wastes tokens and may cause the LLM to reproduce the same content.
- Summary of what failed gives enough context for improvement.
- The editorial service regenerates from scratch with feedback guidance.

### Retry Count
**Recommendation:** Keep at 3 (matching roadmap and existing `route_after_review` logic).
- `route_after_review` already checks `revision_count >= 3`.
- 3 retries is a reasonable balance between quality improvement and resource usage.
- Each retry involves editorial + enrich + review (3 LLM calls minimum), so 3 retries = ~12 total LLM calls max.

### Escalation Handling
**Recommendation:** On escalation (max retries exceeded):
- Set `pipeline_status = "failed"` in the review node when `revision_count >= 3` and review still fails.
- Append a clear escalation message to `error_log`.
- Keep the last `current_draft` in state (do not clear it) -- it represents the best attempt.
- `feedback_history` preserves all failure context for manual review.
- No notification system in Phase 6 (Phase 7 adds admin visibility).

### Escalation Recovery
**Recommendation:** No automatic retry after escalation in Phase 6. Manual recovery (re-running the pipeline) is a Phase 7 concern when admin can trigger re-runs. The graph routes to END on escalation, which is a terminal state.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual quality gates | LLM-as-a-Judge automated evaluation | 2024-2025 | Enables fully automated pipeline without human review for every draft |
| Simple pass/fail on whole content | Per-criterion structured evaluation | 2024-2025 | Allows targeted feedback and selective regeneration |
| Score-based evaluation (1-10) | Pass/fail with severity levels | Current best practice | More actionable for automated pipelines; numeric scores need arbitrary thresholds |
| Full content re-generation on failure | Feedback-guided regeneration | Current best practice | Prevents same errors from repeating; more token-efficient |

## Open Questions

1. **Enrich re-run efficiency on retries**
   - What we know: When review routes back to editorial, the graph follows `editorial -> enrich -> review`. Enrich makes Supabase + Gemini calls each time.
   - What's unclear: Whether repeated enrichment produces meaningfully different results or just adds latency.
   - Recommendation: Accept the re-run for now (it ensures enrichment matches new content). Monitor latency. If it becomes a bottleneck, add a conditional check in enrich node (`revision_count > 0 -> skip if DB data unchanged`). Not a Phase 6 concern.
   - Confidence: MEDIUM

2. **LLM evaluation consistency for hallucination detection**
   - What we know: Gemini with temperature=0.0 and structured output provides relatively consistent results.
   - What's unclear: How well Gemini can detect hallucinated fashion brand names or celebrity references that sound plausible but don't exist in the curated data.
   - Recommendation: Include explicit instructions in the evaluation prompt: "Any brand, celebrity, or event NOT mentioned in the curated data should be flagged as hallucination." Test with known hallucinated content.
   - Confidence: MEDIUM

3. **Review node behavior when editorial returns failed status**
   - What we know: If editorial_node fails, it sets `pipeline_status = "failed"` and `current_draft = None`. But the graph edge `editorial -> enrich -> review` still executes.
   - What's unclear: Whether the graph should short-circuit to END when `pipeline_status = "failed"`.
   - Recommendation: For Phase 6, handle this in the review node by checking `current_draft is not None`. The existing enrich node already handles null draft gracefully. A conditional edge after editorial is a possible optimization but not needed now.
   - Confidence: HIGH

## Sources

### Primary (HIGH confidence)
- Project codebase: `state.py` -- verified `review_result`, `revision_count`, `feedback_history` fields exist with correct types
- Project codebase: `graph.py` -- verified `route_after_review` conditional edge logic, routing paths, and stub_review reference
- Project codebase: `test_graph.py` -- verified existing tests cover happy path, retry, and max retry scenarios
- Project codebase: `editorial_service.py` -- verified structured output pattern, repair loop pattern, Gemini SDK usage
- Project codebase: `curation_service.py` -- verified `retry_on_api_error`, `get_genai_client`, `_strip_markdown_fences` utility patterns
- Project codebase: `models/layout.py` -- verified `MagazineLayout` schema, `model_validate()` for format checking
- Pydantic v2.12.5 docs -- `model_validate()` for dict validation, `model_validate_json()` for JSON string validation

### Secondary (MEDIUM confidence)
- LLM-as-a-Judge evaluation patterns -- established practice in 2024-2025 for automated content evaluation
- LangGraph conditional edge documentation -- `add_conditional_edges` with named targets, return value routing

### Tertiary (LOW confidence)
- Gemini hallucination detection reliability -- no authoritative benchmarks for fashion domain; effectiveness depends on prompt quality

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed; no new dependencies needed
- Architecture: HIGH - follows exact project patterns from prior phases; state schema and graph topology already exist
- Review evaluation design: MEDIUM - LLM-as-a-Judge is established pattern but hallucination detection reliability depends on prompt engineering
- Feedback loop: HIGH - graph routing already tested; editorial modification is straightforward prompt injection
- Pitfalls: MEDIUM - identified from codebase analysis and LLM evaluation experience; some are speculative

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (30 days -- stack is stable; evaluation prompt quality may need iteration)
