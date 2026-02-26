---
phase: 10-pipeline-observability-backend
verified: 2026-02-26T04:24:43Z
status: passed
score: 4/4 must-haves verified
gaps: []
---

# Phase 10: Pipeline Observability Backend Verification Report

**Phase Goal:** 파이프라인 실행 시 각 노드의 토큰 사용량, 처리 시간, 상태가 자동 수집되어 API로 조회 가능한 상태
**Verified:** 2026-02-26T04:24:43Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | 파이프라인을 실행하면 7개 노드 각각의 실행 시간(ms), 토큰 사용량, 성공/실패 상태가 JSONL 파일에 자동 저장된다 | VERIFIED | `node_wrapper` in `graph.py` wraps all 7 nodes (lines 90-91); wrapper captures `started_at`, `ended_at`, `duration_ms` (computed via model_validator), `token_usage`, `status`; `append_node_log` writes to `data/logs/{thread_id}.jsonl`. Unit test confirmed: duration_ms=0.2, total_tokens=150 written correctly. |
| 2  | GET /api/contents/{id}/logs 호출 시 해당 콘텐츠의 노드별 실행 로그가 시간순으로 반환된다 | VERIFIED | `logs.py` route resolves `content_id -> thread_id` via `get_content_by_id()` (which returns full DB row including `thread_id`); reads JSONL via `read_node_logs`; sorts by `started_at`; returns `LogsResponse` with `runs` + `summary`. Router registered in `app.py` line 58 at `/api/contents` prefix before admin router. |
| 3  | 관측성 수집이 실패해도 파이프라인 실행은 중단되지 않는다 (fire-and-forget) | VERIFIED | `node_wrapper.py`: post-flight instrumentation is wrapped in `try/except Exception` (lines 102-107, 164-169); `storage.py`: `append_node_log` and `read_node_logs` both wrapped in `try/except` with `logger.warning`. Manual test confirmed: with storage pointing to non-writable path, node still executes and returns result. |
| 4  | 관측성 데이터가 EditorialPipelineState가 아닌 별도 저장소(로컬 JSONL)에 저장되어 기존 체크포인트와 충돌하지 않는다 | VERIFIED | `state.py` `EditorialPipelineState` has zero observability fields. All node logs written to `data/logs/{thread_id}.jsonl` via `storage.py`. The node_wrapper writes logs AFTER extracting data from the state — no mutation of state object. Checkpoint saver only serializes `EditorialPipelineState` TypedDict. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/editorial_ai/observability/__init__.py` | Package exports | VERIFIED | 27 lines; exports all 8 public symbols |
| `src/editorial_ai/observability/models.py` | NodeRunLog, TokenUsage, PipelineRunSummary Pydantic models | VERIFIED | 142 lines; computed `duration_ms` and token sums via `model_validator(mode='before')`; `from_logs()` aggregation confirmed working |
| `src/editorial_ai/observability/collector.py` | ContextVar-based token accumulation | VERIFIED | 71 lines; `reset_token_collector`, `record_token_usage`, `harvest_tokens` all implemented; fire-and-forget with try/except |
| `src/editorial_ai/observability/storage.py` | JSONL file append/read | VERIFIED | 65 lines; `append_node_log` and `read_node_logs`; fire-and-forget; one file per `thread_id` at `data/logs/{thread_id}.jsonl` |
| `src/editorial_ai/observability/node_wrapper.py` | Decorator factory for node instrumentation | VERIFIED | 179 lines; handles both async and sync nodes; captures timing + state snapshots + token harvest + error details; re-raises node errors after logging |
| `src/editorial_ai/api/routes/logs.py` | GET /{content_id}/logs endpoint | VERIFIED | 99 lines; resolves content_id, reads/sorts logs, builds LogsResponse with summary; `include_io` query param |
| `src/editorial_ai/api/schemas.py` | Observability response schemas | VERIFIED | Added TokenUsageResponse, NodeRunLogResponse, PipelineRunSummaryResponse, LogsResponse (lines 70-122) |
| `src/editorial_ai/graph.py` | node_wrapper applied to all 7 nodes | VERIFIED | Lines 90-91: `for name in list(nodes.keys()): nodes[name] = node_wrapper(name)(nodes[name])`; all 7 nodes in dict (curation, source, editorial, enrich, review, admin_gate, publish) |
| `data/logs/.gitkeep` | Log directory placeholder | VERIFIED | Directory exists at `data/logs/`; `.gitkeep` present; `.gitignore` excludes `data/logs/*.jsonl` (line 20) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `graph.py` `build_graph()` | `node_wrapper` | `from editorial_ai.observability import node_wrapper` | WIRED | Line 20 import; lines 90-91 loop applies to all nodes in dict |
| `node_wrapper` | `collector` | `reset_token_collector`, `harvest_tokens` | WIRED | Lines 23-24 import; called at start/end of every node execution |
| `node_wrapper` | `storage` | `append_node_log` | WIRED | Line 26 import; called in post-flight instrumentation block |
| Services (4 files) | `record_token_usage` | `from editorial_ai.observability import record_token_usage` | WIRED | curation_service: 3 call sites (lines 131, 156, 195); editorial_service: 4 call sites (lines 135, 190, 263, 322); review_service: 1 call site (line 108); enrich_service: 2 call sites (lines 84, 140) |
| `api/app.py` | `logs.router` | `include_router(logs.router, prefix="/api/contents")` | WIRED | Line 58; registered before admin router to ensure route precedence |
| `logs.py` endpoint | `get_content_by_id` | `from editorial_ai.services.content_service import get_content_by_id` | WIRED | Line 34; returns DB row including `thread_id` column |
| `logs.py` endpoint | `read_node_logs` | `from editorial_ai.observability.storage import read_node_logs` | WIRED | Line 41; reads JSONL file for resolved thread_id |

### Requirements Coverage

| Requirement | Status | Notes |
|-------------|--------|-------|
| 노드별 실행 시간(ms) 자동 수집 | SATISFIED | `duration_ms` computed from `started_at`/`ended_at` via model_validator |
| 노드별 토큰 사용량 자동 수집 | SATISFIED | ContextVar collector + 10 LLM call sites instrumented |
| 노드별 성공/실패 상태 자동 수집 | SATISFIED | `status: Literal["success", "error", "skipped"]` in NodeRunLog |
| JSONL 별도 저장소 (체크포인트 충돌 없음) | SATISFIED | EditorialPipelineState has zero observability fields; JSONL written independently |
| GET /api/contents/{id}/logs API | SATISFIED | Endpoint implemented, registered, returns chronological logs with summary |
| 관측성 수집 실패시 파이프라인 미중단 | SATISFIED | Both node_wrapper and storage layer are fire-and-forget with try/except |

### Anti-Patterns Found

No stub patterns, TODO/FIXME comments, placeholder content, or empty implementations found in any observability files.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | - | - | - |

### Human Verification Required

The following items require a real pipeline run with LLM calls to fully verify:

#### 1. End-to-End Token Capture Across All 7 Nodes

**Test:** Trigger a real pipeline run via `POST /api/pipeline/trigger`, then call `GET /api/contents/{id}/logs`
**Expected:** Response contains 7 NodeRunLogResponse entries (curation, source, editorial, enrich, review, admin_gate, publish), each with non-zero `duration_ms` and non-empty `token_usage` arrays for LLM-calling nodes
**Why human:** Requires live LLM API keys (Gemini) and Supabase connection to execute real nodes

#### 2. Chronological Ordering Across Concurrent Log Writes

**Test:** Run pipeline and verify returned `runs` array is strictly ordered by `started_at` ascending
**Expected:** curation -> source -> editorial -> enrich -> review order in logs
**Why human:** Cannot verify ordering without real async execution with real timestamps

### Gaps Summary

No gaps. All 4 success criteria are structurally implemented and verified:
1. All 7 nodes are wrapped by `node_wrapper` in `build_graph()` — timing, tokens, and status are captured automatically
2. `GET /api/contents/{id}/logs` endpoint is fully implemented, wired, and returns chronological logs
3. Both `node_wrapper` and `storage.py` are fire-and-forget — storage failures log warnings but never raise
4. `EditorialPipelineState` has zero observability fields — JSONL storage is completely separate from LangGraph checkpoints

---
_Verified: 2026-02-26T04:24:43Z_
_Verifier: Claude (gsd-verifier)_
