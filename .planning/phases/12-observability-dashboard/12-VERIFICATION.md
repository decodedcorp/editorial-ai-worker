---
phase: 12-observability-dashboard
verified: 2026-02-26T09:04:20Z
status: human_needed
score: 2.5/3 must-haves verified
human_verification:
  - test: "콘텐츠 상세 페이지 Pipeline 탭에서 실제 로그 데이터가 있는 콘텐츠 열기"
    expected: "노드별 Gantt 타임라인 바가 표시되고, 각 바에 노드명, 소요시간, 성공/실패 색상이 적용된다. 바 클릭 시 토큰 사용량과 예상 비용이 패널에 표시된다."
    why_human: "BFF proxy가 실제 FastAPI 백엔드(Phase 10)와 통신해야 하므로, 백엔드 실행 환경 없이 데이터 흐름을 프로그래밍적으로 검증 불가"
  - test: "로그가 없는 콘텐츠의 Pipeline 탭 확인"
    expected: "'No pipeline logs available for this content.' 빈 상태 메시지가 표시된다."
    why_human: "빈 상태 렌더링은 코드로 확인했으나 실제 UI 동작 확인 필요"
  - test: "콘텐츠 목록 페이지에서 Pipeline 컬럼의 상태 표시 확인"
    expected: "각 항목에 5개 도트 + 뱃지('Awaiting Approval', 'Approved', 'Rejected', 'Published')가 표시된다. 로그 데이터가 있는 항목은 소요시간, 예상 비용, 재시도 횟수도 표시된다."
    why_human: "BFF가 목록 조회 시 각 항목의 로그를 병렬로 가져오는 동작은 실제 백엔드 없이 확인 불가"
  - test: "성공 기준 3 부분 충족 여부 — '큐레이션 중/리뷰 중' 상태 표시"
    expected: "요구사항 OBS-06은 '큐레이션 중/리뷰 중/승인 대기 중'을 명시하나, 구현은 DB 터미널 상태(pending/approved/rejected/published)만 처리함. 파이프라인 실행 중(in-flight) 콘텐츠가 목록에 나타난다면 Unknown 상태로 표시되거나 누락될 수 있음."
    why_human: "파이프라인 실행 중 콘텐츠 항목이 실제로 목록에 나타나는지, 그리고 PipelineStatusIndicator가 해당 상태를 graceful하게 처리하는지 확인 필요 (STATUS_MAP에 없는 키는 null 반환)"
---

# Phase 12: Observability Dashboard Verification Report

**Phase Goal:** Admin 대시보드에서 파이프라인 실행 과정을 시각적으로 추적하고 비용을 파악할 수 있는 상태
**Verified:** 2026-02-26T09:04:20Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | 콘텐츠 상세 페이지에서 노드별 실행 타임라인(노드명, 소요시간, 성공/실패)을 시각적으로 확인할 수 있다 | ✓ VERIFIED | `pipeline-tab.tsx` (179줄) + `timeline-bar.tsx` (78줄) — groupByRounds, TimelineBar 렌더링, 에러 색상 처리, ContentTabs에 Pipeline 탭 연결, 상세 페이지에서 parallel fetch |
| 2  | 각 노드의 토큰 사용량과 예상 비용(Gemini 2.5 Flash 가격 기준)이 로그 패널에 표시된다 | ✓ VERIFIED | `node-detail-panel.tsx` (182줄) — `estimateCost` + `formatCost` 호출, 토큰 breakdown 렌더링. `cost-utils.ts` (51줄) — Gemini 2.5 Flash 가격($0.30/$2.50 per 1M) 하드코딩. `cost-summary-card.tsx` (84줄) — 4-metric grid |
| 3  | 콘텐츠 목록 페이지에서 각 항목의 파이프라인 진행 상태(큐레이션 중/리뷰 중/승인 대기 중)를 한눈에 파악할 수 있다 | ? PARTIAL | `pipeline-status-indicator.tsx` (109줄) — 5개 도트 + 뱃지 구현됨. '승인 대기 중'(pending) 처리됨. 그러나 '큐레이션 중'/'리뷰 중' 상태는 DB에 터미널 상태만 저장된다는 아키텍처 제약으로 미구현. 플랜에서 의도적 설계 결정으로 문서화됨 |

**Score:** 2/3 truths fully verified (1 partial/human-needed)

### Required Artifacts

| Artifact | Lines | Exists | Substantive | Wired | Status |
|----------|-------|--------|-------------|-------|--------|
| `admin/src/app/api/contents/[id]/logs/route.ts` | 32 | ✓ | ✓ | ✓ | ✓ VERIFIED |
| `admin/src/components/pipeline/cost-utils.ts` | 51 | ✓ | ✓ | ✓ | ✓ VERIFIED |
| `admin/src/components/pipeline/pipeline-tab.tsx` | 179 | ✓ | ✓ | ✓ | ✓ VERIFIED |
| `admin/src/components/pipeline/timeline-bar.tsx` | 78 | ✓ | ✓ | ✓ | ✓ VERIFIED |
| `admin/src/components/pipeline/node-detail-panel.tsx` | 182 | ✓ | ✓ | ✓ | ✓ VERIFIED |
| `admin/src/components/pipeline/cost-summary-card.tsx` | 84 | ✓ | ✓ | ✓ | ✓ VERIFIED |
| `admin/src/components/pipeline-status-indicator.tsx` | 109 | ✓ | ✓ | ✓ | ✓ VERIFIED |
| `admin/src/app/api/contents/route.ts` (BFF enrichment) | 103 | ✓ | ✓ | ✓ | ✓ VERIFIED |
| `admin/src/lib/types.ts` (observability types) | - | ✓ | ✓ | ✓ | ✓ VERIFIED |
| `admin/src/components/content-table.tsx` (Pipeline column) | 229 | ✓ | ✓ | ✓ | ✓ VERIFIED |
| `admin/src/app/contents/[id]/page.tsx` (parallel fetch) | 122 | ✓ | ✓ | ✓ | ✓ VERIFIED |
| `admin/src/app/contents/page.tsx` (list page wiring) | 71 | ✓ | ✓ | ✓ | ✓ VERIFIED |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `contents/[id]/page.tsx` | `/api/contents/{id}/logs` | `Promise.all + apiGet` | ✓ WIRED | Line 22-27: parallel fetch with graceful fallback (`catch(() => null)`) |
| `content-tabs.tsx` | `PipelineTab` | import + `<TabsContent value="pipeline">` | ✓ WIRED | Line 5, 41-43: Pipeline tab fully integrated |
| `pipeline-tab.tsx` | `CostSummaryCard`, `TimelineBar`, `NodeDetailPanel` | import + render | ✓ WIRED | All 3 sub-components rendered with real data |
| `node-detail-panel.tsx` | `estimateCost`, `formatCost` | import + per-tu calculation | ✓ WIRED | Lines 66-86: cost calculated and rendered per token usage entry |
| `PipelineTab` → IO lazy load | `/api/contents/{contentId}/logs?include_io=true` | `loadIoData` callback | ✓ WIRED | Lines 57-71: fetch call with response assignment to `fullLogs` state |
| `content-table.tsx` | `PipelineStatusIndicator` | import + Pipeline column | ✓ WIRED | Lines 26, 67-75: Pipeline column renders indicator with `status` + `pipeline_summary` |
| `contents/route.ts` (BFF list) | FastAPI logs endpoint | `Promise.all` parallel fetch | ✓ WIRED | Lines 50-92: each item's logs fetched, `estimateCost` applied, retry count derived |
| `contents/page.tsx` | `ContentListWithSummaryResponse` type | `apiGet` with typed response | ✓ WIRED | Line 29: uses `ContentListWithSummaryResponse` |

### Requirements Coverage

| Requirement | Description | Status | Notes |
|-------------|-------------|--------|-------|
| OBS-04 | Admin 상세 페이지에 노드별 타임라인 로그 패널 (토큰/시간/프롬프트 확인) | ✓ SATISFIED | `PipelineTab` + `TimelineBar` + `NodeDetailPanel` 구현됨. 프롬프트 확인은 IO 데이터 lazy load로 제공 |
| OBS-05 | 토큰 비용 추정 표시 (Gemini 2.5 Flash 가격 기반) | ✓ SATISFIED | `cost-utils.ts` Gemini 2.5 Flash 가격 내장, `NodeDetailPanel` + `CostSummaryCard`에 표시 |
| OBS-06 | 콘텐츠 목록 페이지에 파이프라인 진행 상태 표시 (큐레이션 중/리뷰 중/대기 중) | ? PARTIAL | '대기 중'(Awaiting Approval/pending) 구현됨. '큐레이션 중'/'리뷰 중'은 DB가 터미널 상태만 저장하는 아키텍처 제약으로 구현 안 됨. 12-03-PLAN에 의도적 설계 결정으로 문서화됨. 실행 중인 콘텐츠가 목록에 나타날 경우 `PipelineStatusIndicator`가 `null` 반환 (graceful but invisible) |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `pipeline-status-indicator.tsx` | 62 | `return null` when status not in STATUS_MAP | Info | '큐레이션 중'/'리뷰 중' 상태의 in-flight 콘텐츠가 목록에 나타날 경우 Pipeline 컬럼이 비어 보일 수 있음. 현재 시스템 아키텍처상 이런 상태의 항목은 목록에 노출되지 않을 가능성 높음 |
| `app/api/contents/route.ts` | 60, 62, 89 | `return null` (3곳) | Info | 모두 graceful fallback 패턴 — 로그 없는 항목은 `pipeline_summary: null` 반환, 정상 동작 |

### Human Verification Required

#### 1. Pipeline Tab — 실제 로그 데이터 표시

**Test:** FastAPI 백엔드가 실행 중인 환경에서, 로그가 있는 콘텐츠의 상세 페이지를 열고 Pipeline 탭 클릭
**Expected:** Gantt 타임라인 바들이 표시되고, 각 바에 노드명, 소요시간, 성공/실패 색상이 표시된다. 바를 클릭하면 NodeDetailPanel이 열리며 토큰 수량과 예상 비용(`~$0.0xxx`)이 표시된다.
**Why human:** BFF proxy → FastAPI 백엔드 연결은 실제 실행 환경 필요

#### 2. Cost Summary Card — 4-metric grid 표시

**Test:** 로그가 있는 콘텐츠의 Pipeline 탭 상단 CostSummaryCard 확인
**Expected:** Total Duration, Total Tokens, Estimated Cost, Nodes 4개 메트릭이 표시된다. Estimated Cost는 `~$0.03` 형식으로 표시된다.
**Why human:** 실제 token usage 데이터가 있어야 비용 계산 검증 가능

#### 3. List Page — Pipeline 컬럼 + 메트릭 표시

**Test:** 콘텐츠 목록 페이지에서 여러 항목의 Pipeline 컬럼 확인
**Expected:** 각 행에 5개 도트 + 상태 뱃지가 표시된다. 로그가 있는 항목은 두 번째 줄에 소요시간(`3.2s`), 예상 비용(`~$0.03`), 재시도 횟수(`1 retry`) 중 해당되는 항목이 표시된다.
**Why human:** BFF 병렬 로그 조회 동작 확인을 위해 실제 환경 필요

#### 4. OBS-06 부분 충족 확인 — in-flight 콘텐츠 처리

**Test:** 파이프라인이 실행 중인 콘텐츠(아직 DB 상태 변경 전)가 목록에 표시되는지, 그리고 Pipeline 컬럼이 빈 것인지 확인
**Expected:** 현재 구현상 Pipeline 컬럼이 비어 보이거나 상태가 없을 수 있음. 이것이 허용 가능한 UX인지, 또는 '진행 중' 상태 표시가 필요한지 제품 결정 필요.
**Why human:** 아키텍처 설계 제약에 의한 부분 구현 — 요구사항과 실제 사용 패턴 간 갭을 제품 오너가 확인해야 함

### Gaps Summary

모든 아티팩트가 존재하고 실질적인 구현을 포함하며 올바르게 연결되어 있다. 자동화 검증에서 코드 수준 스텁이나 미연결 컴포넌트는 발견되지 않았다.

**부분 구현 사항 (설계 결정):**

성공 기준 3("콘텐츠 목록 페이지에서 큐레이션 중/리뷰 중/승인 대기 중 파악")에서 '큐레이션 중'/'리뷰 중' 상태가 구현되지 않았다. 12-03-PLAN은 이를 의도적 설계 결정으로 문서화했다: 콘텐츠 DB는 터미널 상태(pending/approved/rejected/published)만 저장하며, 파이프라인 실행 중 상태는 WebSocket/폴링 없이 실시간으로 표시할 수 없다. 세밀한 파이프라인 진행 상태는 상세 페이지의 Pipeline 탭에서 확인 가능하다.

이 설계 결정이 OBS-06 요구사항을 완전히 충족하는지, 또는 요구사항 업데이트가 필요한지는 제품 오너 결정 사항이다.

---

_Verified: 2026-02-26T09:04:20Z_
_Verifier: Claude (gsd-verifier)_
