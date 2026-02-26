---
phase: quick-003
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/run_pipeline_fast.py
  - scripts/run_pipeline_multi.py
  - scripts/run_pipeline_test.py
autonomous: true

must_haves:
  truths:
    - "Local script pipeline runs produce logs in data/logs/{uuid}.jsonl matching the content's thread_id"
    - "Content detail page in admin shows execution logs for locally-generated content"
  artifacts:
    - path: "scripts/run_pipeline_fast.py"
      provides: "thread_id in initial_state"
      contains: "thread_id"
    - path: "scripts/run_pipeline_multi.py"
      provides: "thread_id in initial_state"
      contains: "thread_id"
    - path: "scripts/run_pipeline_test.py"
      provides: "thread_id in initial_state"
      contains: "thread_id"
  key_links:
    - from: "scripts/*.py initial_state"
      to: "src/editorial_ai/observability/node_wrapper.py"
      via: "state['thread_id'] flows through graph to node_wrapper log storage"
      pattern: "thread_id.*uuid"
---

<objective>
Fix pipeline execution logs not appearing on the content detail page for locally-run pipelines.

Purpose: Local scripts (run_pipeline_fast.py, run_pipeline_multi.py, run_pipeline_test.py) do not set `thread_id` in `initial_state`. The node_wrapper falls back to "unknown", writing logs to `data/logs/unknown.jsonl`. Meanwhile, auto_approve_admin_gate saves the content with `thread_id = keyword` (e.g., "NewJeans 패션"). The mismatch means the logs API returns empty for that content.

Output: All three scripts set `"thread_id": str(uuid.uuid4())` in their `initial_state` dict, matching the pattern used by the API trigger (`pipeline.py` line 48/56).
</objective>

<execution_context>
@/Users/kiyeol/.claude-pers/get-shit-done/workflows/execute-plan.md
@/Users/kiyeol/.claude-pers/get-shit-done/templates/summary.md
</execution_context>

<context>
# Root cause chain:
# 1. node_wrapper.py:89 — state.get("thread_id", "unknown") -> logs go to unknown.jsonl
# 2. admin_gate.py:43 — state.get("thread_id") or keyword or "unknown" -> content gets keyword as thread_id
# 3. logs.py:38 — content["thread_id"] used to look up log file -> file doesn't exist -> empty logs
#
# Fix pattern (from API trigger pipeline.py:48-56):
#   thread_id = str(uuid.uuid4())
#   initial_state = { "thread_id": thread_id, ... }

@scripts/run_pipeline_fast.py
@scripts/run_pipeline_multi.py
@scripts/run_pipeline_test.py
@src/editorial_ai/observability/node_wrapper.py
@src/editorial_ai/api/routes/pipeline.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add thread_id to initial_state in all local scripts</name>
  <files>
    scripts/run_pipeline_fast.py
    scripts/run_pipeline_multi.py
    scripts/run_pipeline_test.py
  </files>
  <action>
    For each of the three scripts:

    1. Add `import uuid` to the imports section (near existing `import asyncio`, `import time`)

    2. In the function that builds `initial_state`, generate a UUID and include it:

    **run_pipeline_fast.py** (line ~276, `run_pipeline()` function):
    ```python
    thread_id = str(uuid.uuid4())
    initial_state = {
        "thread_id": thread_id,
        "curation_input": { ... },  # keep existing
    }
    ```
    Also print the thread_id so the user can cross-reference:
    ```python
    print(f'>>> thread_id: {thread_id}', flush=True)
    ```

    **run_pipeline_multi.py** (line ~557, `run_scenario()` function):
    Each scenario invocation needs its own UUID. Add `import uuid` at top.
    In `run_scenario()`, before building `initial_state`:
    ```python
    thread_id = str(uuid.uuid4())
    initial_state = {
        "thread_id": thread_id,
        "curation_input": { ... },  # keep existing
    }
    ```
    Print thread_id in the scenario header output.

    **run_pipeline_test.py** (line ~69, `run_pipeline()` function):
    Same pattern — `import uuid`, generate thread_id, add to initial_state, print it.

    DO NOT modify any other logic. The auto_approve_admin_gate in each script already handles
    `state.get("thread_id") or keyword or "unknown"` — with thread_id now present in state,
    it will use the UUID instead of falling back to keyword.
  </action>
  <verify>
    1. `grep -n "import uuid" scripts/run_pipeline_fast.py scripts/run_pipeline_multi.py scripts/run_pipeline_test.py` — all three have the import
    2. `grep -n '"thread_id"' scripts/run_pipeline_fast.py scripts/run_pipeline_multi.py scripts/run_pipeline_test.py` — all three have thread_id in initial_state
    3. `python -c "import scripts.run_pipeline_fast; import scripts.run_pipeline_multi; import scripts.run_pipeline_test"` — no import errors (syntax check)
  </verify>
  <done>
    All three local scripts include `"thread_id": str(uuid.uuid4())` in their initial_state dict. Node wrapper will now write logs to `data/logs/{uuid}.jsonl` and admin_gate will save the same UUID as the content's thread_id, making logs retrievable from the content detail page.
  </done>
</task>

</tasks>

<verification>
- All three scripts have `import uuid` and `"thread_id"` in initial_state
- No other logic changed (auto_approve_admin_gate, stub functions, etc. remain identical)
- The fix follows the exact same pattern as the API trigger in `src/editorial_ai/api/routes/pipeline.py`
</verification>

<success_criteria>
- `grep "thread_id" scripts/run_pipeline_fast.py` shows thread_id in initial_state
- `grep "thread_id" scripts/run_pipeline_multi.py` shows thread_id in initial_state
- `grep "thread_id" scripts/run_pipeline_test.py` shows thread_id in initial_state
- Scripts parse without syntax errors
</success_criteria>

<output>
After completion, create `.planning/quick/003-content-detail-pipeline-execution-logs/003-SUMMARY.md`
</output>
