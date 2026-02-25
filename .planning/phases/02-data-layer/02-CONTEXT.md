# Phase 2: Data Layer - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

파이프라인이 Supabase DB와 안정적으로 통신하고, 그래프 상태가 Postgres에 영속화되는 상태를 구축한다. 셀럽/상품/포스트 데이터 조회 서비스 레이어와 AsyncPostgresSaver 체크포인터를 포함한다. 데이터 생성/수정은 Phase 2 범위가 아니며, 후속 Phase에서 품질을 확인한 후 결정한다.

</domain>

<decisions>
## Implementation Decisions

### Supabase 접근 방식
- supabase-py SDK 사용 (REST API 기반)
- service_role key로 RLS 바이패스 (백엔드 서비스이므로 전체 데이터 접근 필요)
- 기존 Phase 1의 pydantic-settings 패턴을 확장하여 연결 설정 관리 (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

### 서비스 레이어 범위와 스키마
- Phase 2에서는 Read 위주: 셀럽/상품/포스트 조회 기능 구현
- 데이터 생성(Create/Update)은 후속 Phase에서 처리 — 먼저 조회 품질을 확인한 후 결정
- 기존 Supabase에 셀럽/상품/포스트 테이블 이미 존재 — 실제 스키마는 Phase 2 구현 시 Supabase에서 확인하여 매핑
- 셀럽/상품 검색은 Supabase 텍스트 검색(PostgreSQL full-text search 또는 ILIKE) 활용

### 체크포인터 저장 전략
- AsyncPostgresSaver 사용
- lean state 원칙 적용: state에는 ID/참조만, 전체 페이로드는 Supabase에 저장

### Claude's Discretion
- 체크포인터용 DB 인스턴스 결정 (같은 Supabase DB vs 별도)
- lean state에서 ID와 중간 결과물의 구체적 경계 설계
- 중단/재개 시나리오 설계 (Admin HITL interrupt, 장애 복구 등)
- 체크포인터 데이터 보존 기간 및 정리 정책
- thread_id 관리 전략 (키워드-thread 매핑 등)
- 체크포인터 테스트 방식 (MemorySaver mock, SQLite 로컬 등)

</decisions>

<specifics>
## Specific Ideas

- 포스트 기반 데이터는 실제 데이터와 목업 기반으로 조회 테스트를 먼저 수행 — 생성/저장은 품질 확인 후 결정
- Supabase가 단일 프로젝트(dev/prod 미분리)이므로 테스트 시 데이터 수정/삭제 절대 금지
- 서비스 레이어 테스트는 Read-only로 제한하고, 쓰기 테스트는 mock으로 대체

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-data-layer*
*Context gathered: 2026-02-25*
