---
phase: quick-003
plan: 01
subsystem: pipeline-scripts
tags: [thread_id, observability, logs, pipeline]
dependency-graph:
  requires: []
  provides: [thread_id-in-local-scripts]
  affects: [content-detail-logs-api]
tech-stack:
  added: []
  patterns: [uuid-thread-id-tracking]
key-files:
  created: []
  modified:
    - scripts/run_pipeline_fast.py
    - scripts/run_pipeline_multi.py
    - scripts/run_pipeline_test.py
decisions: []
metrics:
  duration: "2m"
  completed: 2026-02-26
---

# Quick Task 003: Content Detail Pipeline Execution Logs Fix

UUID thread_id generation in all 3 local pipeline scripts so node_wrapper logs match content records.

## What Was Done

### Task 1: Add thread_id to initial_state in all local scripts

**Root cause:** Local scripts did not set `thread_id` in `initial_state`. The node_wrapper fell back to `"unknown"`, writing logs to `data/logs/unknown.jsonl`. Meanwhile, `auto_approve_admin_gate` saved `keyword` as `thread_id` (e.g., "NewJeans 패션"). This mismatch meant the logs API returned empty for that content.

**Fix applied to all 3 scripts:**

1. Added `import uuid` to imports
2. Generated `thread_id = str(uuid.uuid4())` before building `initial_state`
3. Included `"thread_id": thread_id` in `initial_state` dict
4. Added `print(f">>> thread_id: {thread_id}")` for cross-referencing

**Files modified:**
- `scripts/run_pipeline_fast.py` -- thread_id in `run_pipeline()` function
- `scripts/run_pipeline_multi.py` -- unique thread_id per scenario in `run_scenario()` function
- `scripts/run_pipeline_test.py` -- thread_id in `run_pipeline()` function

**Data flow after fix:**
1. Script generates UUID -> passes in `initial_state["thread_id"]`
2. `node_wrapper.py` reads `state["thread_id"]` -> writes logs to `data/logs/{uuid}.jsonl`
3. `auto_approve_admin_gate` reads `state["thread_id"]` -> saves UUID as content's `thread_id`
4. Logs API reads `content["thread_id"]` -> finds matching log file -> returns logs

**Commit:** 7463a58

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- All 3 scripts have `import uuid` (confirmed via grep)
- All 3 scripts have `"thread_id"` in initial_state (confirmed via grep)
- All 3 scripts parse without syntax errors (confirmed via ast.parse)
- No other logic changed (auto_approve_admin_gate, stubs remain identical)
- Fix follows the exact same pattern as API trigger in `src/editorial_ai/api/routes/pipeline.py`
