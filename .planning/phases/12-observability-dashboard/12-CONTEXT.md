# Phase 12: Observability Dashboard - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Admin 대시보드에서 파이프라인 실행 과정을 시각적으로 추적하고 비용을 파악할 수 있는 상태. Phase 10에서 구축한 observability 백엔드(JSONL 저장, `/api/contents/{id}/logs` API)의 데이터를 Admin UI에 시각화하는 것이 범위. 새로운 메트릭 수집이나 백엔드 변경은 범위 밖.

</domain>

<decisions>
## Implementation Decisions

### 타임라인 시각화
- 하이브리드 방식: 수평 바 차트(Gantt 스타일)로 전체 타임라인 표시 + 노드 클릭 시 상세 정보 펼침
- 콘텐츠 상세 페이지에 별도 "Pipeline" 탭으로 추가 (기존 Magazine / JSON 탭 옆)
- 노드 클릭 시 펼쳐지는 상세 정보: 토큰 사용량, LLM 호출 횟수, 에러 상세, 입출력 데이터(JSON) 모두 포함

### 비용/토큰 표시
- 노드별 개별 수치 + 파이프라인 전체 총합 모두 표시
- 모델별 동적 가격 반영 (Phase 13 모델 라우팅 도입 대비, 현재는 Gemini 2.5 Flash 기준)
- 상세 수치 형식: "1,240 input + 890 output = 2,130 tokens" 스타일로 input/output 분리 표시

### 목록 페이지 상태 표시
- 텍스트 배지 + 스텝 인디케이터 병행 표시 (e.g. ●●●○○ [큐레이션 중])
- 목록 항목에 추가 정보: 총 소요시간, 총 비용, 재시도 횟수
- 목록은 새로고침 시에만 상태 업데이트 (실시간 폴링 없음)

### Claude's Discretion
- 타임라인 실시간 업데이트 여부 (실행 중 폴링 vs 완료 후 표시)
- 비용 요약 카드 위치 (Pipeline 탭 내부 vs 상세 페이지 상단)
- 목록 페이지 상태 필터링 여부 및 방식
- 에러/실패 시각적 구분 방법 (색상, 아이콘, 배너 등)
- Review loop 재시도 타임라인 표현 방식 (회차 표시 vs 별도 바)
- 에스컬레이션 상태 특별 표시 여부
- 에러 상세 정보 표현 방식 (원본 vs 요약+토글)

</decisions>

<specifics>
## Specific Ideas

- 목록 페이지 ASCII mockup에서 보인 "배지 + 스텝" 조합 — 배지로 현재 단계명, 스텝으로 진행도 시각화
- 타임라인의 하이브리드 방식 — Gantt 바로 전체 흐름을 한눈에, 클릭으로 드릴다운하는 2-level 구조
- 토큰 수치는 간결하지 않고 정확한 숫자로 (개발자/관리자 대상이므로 상세 수치 선호)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-observability-dashboard*
*Context gathered: 2026-02-26*
