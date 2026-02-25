# Phase 7: Admin Backend + HITL - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

검수 통과(Review pass) 콘텐츠를 Supabase에 저장하고, 관리자가 FastAPI 엔드포인트로 승인/반려하며, LangGraph interrupt 패턴으로 파이프라인이 승인 대기 중 일시정지되는 백엔드 시스템을 구축한다. 대시보드 UI는 Phase 8에서 별도 구현.

</domain>

<decisions>
## Implementation Decisions

### 콘텐츠 저장 정책
- 반려 시 사유(rejection reason) 필수 입력

### HITL Interrupt 동작
- Review pass 직후 admin_gate 노드에서 interrupt — 검수 통과된 콘텐츠만 관리자에게 도달
- 승인 시 publish 노드로 진행, 반려 시 editorial 노드로 재실행 (Command(resume=) 값으로 분기)

### Claude's Discretion
- 저장 단위: 전체 Layout JSON jsonb vs 정규화 분리 — 프로젝트 상황에 맞게 판단
- 상태 모델: 3단계(pending/approved/published) vs 4단계(rejected 별도) — 반려 사유 필수이므로 적절한 모델 선택
- 버전 관리: V1에서 히스토리 필요 여부 판단
- 큐레이션 컨텍스트 함께 저장 여부: 체크포인터에 이미 있으므로 중복 여부 판단
- API 프레임워크: 로드맵에 FastAPI 명시되어 있으나 최종 선택은 Claude 재량
- 인증/권한: V1 내부 도구이므로 인증 없이 진행 vs 간단한 API Key — 상황에 맞게
- 관리자 알림: V1에서 알림 없이 대시보드 직접 확인 vs 간단한 Webhook — 판단
- 타임아웃: 무기한 대기 vs 설정 가능한 타임아웃 — 판단
- 반려 후 처리: 자동 재생성(피드백 주입 후 editorial 재실행) vs 수동 재트리거 — 판단
- 발행 동작: 상태 변경만 vs 외부 시스템 연동 포함 — V1 범위에 맞게
- 파이프라인 종료 상태: pipeline_status 갱신 방식 및 로깅 범위
- 콘텐츠 조회 API 포함 여부: 이 페이즈 vs Phase 8
- 파이프라인 트리거 API 포함 여부: API 엔드포인트 vs CLI/스크립트만

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-admin-backend-hitl*
*Context gathered: 2026-02-25*
