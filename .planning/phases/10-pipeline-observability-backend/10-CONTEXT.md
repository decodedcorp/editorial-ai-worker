# Phase 10: Pipeline Observability Backend - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

파이프라인 실행 시 각 노드의 토큰 사용량, 처리 시간, 상태를 자동 수집하여 API로 조회 가능한 상태. 대시보드 UI(Phase 12)는 별도 페이즈.

</domain>

<decisions>
## Implementation Decisions

### 수집 메트릭 범위
- 기본 메트릭: 실행 시간(ms), input/output 토큰 수, 성공/실패 상태
- 모델 정보: 사용된 모델명(gemini-2.5-flash 등), 프롬프트 길이(chars)
- 노드 IO: 각 노드의 input/output state를 전체 JSON으로 저장 (디버깅용)
- 비용 계산: Claude 재량 (토큰 수 저장 후 계산 방식 결정)
- 에러 정보: Claude 재량 (적절한 수준으로 구현)

### 수집 메커니즘
- 커스텀 node_wrapper 데코레이터 패턴 (google-genai SDK 직접 사용이므로 LangChain callbacks 불가)
- **Supabase에 저장하지 않음** — 로컬 파일로 저장
- 파일 포맷: Claude 재량 (JSONL, JSON 등 적절한 포맷 선택)
- fire-and-forget: 관측성 수집 실패 시 파이프라인 실행 중단 없음

### API 응답 형태
- GET /api/contents/{id}/logs: 노드별 실행 로그 + 전체 요약(total_duration, total_tokens 등) 포함
- IO 데이터 반환 방식: Claude 재량 (한번에 전부 vs 별도 엔드포인트 분리)
- 빈 상태/실시간 로그 처리: Claude 재량

### run 식별 체계
- 동일 콘텐츠의 다수 실행(재시도, 반려 후 재생성) 구분 방식: Claude 재량
- Review 피드백 루프 내 반복 추적 방식: Claude 재량

### Claude's Discretion
- 에러 로깅 수준 (타입+메시지 vs traceback 포함)
- 비용 계산 타이밍 (저장 시 vs API 응답 시)
- 로컬 파일 포맷 및 디렉토리 구조
- IO 데이터 API 반환 방식
- 빈 로그/실행 중 로그 API 응답 전략
- run/attempt 식별 체계

</decisions>

<specifics>
## Specific Ideas

- Supabase insert 없이 로컬 파일 기반 저장 — 관측성 데이터를 DB에 넣지 않겠다는 명확한 결정
- 전체 노드 IO를 저장하여 디버깅 시 활용 가능하도록

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-pipeline-observability-backend*
*Context gathered: 2026-02-26*
