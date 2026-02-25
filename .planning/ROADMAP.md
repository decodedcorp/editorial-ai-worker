# Roadmap: Editorial AI Worker

## Overview

키워드 하나로 패션 에디토리얼 콘텐츠를 자동 생성하는 멀티 에이전트 파이프라인을 구축한다. Foundation(그래프 스켈레톤 + 데이터 레이어)에서 시작하여 Curation -> Editorial -> Review -> Admin 순서로 파이프라인 노드를 하나씩 완성하며, 각 Phase는 이전 Phase의 출력을 실제 입력으로 사용하여 검증할 수 있는 단위로 설계되었다. 마지막으로 Admin Dashboard UI를 별도 Phase로 분리하여 API와 프론트엔드 관심사를 독립적으로 개발한다.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Graph Skeleton + LLM Integration** - LangGraph StateGraph 스켈레톤과 Vertex AI(Gemini) 연동
- [x] **Phase 2: Data Layer** - Supabase 서비스 레이어와 Postgres 체크포인터 구축
- [x] **Phase 3: Curation Agent** - Gemini + Google Search Grounding 기반 트렌드 키워드 수집 에이전트
- [x] **Phase 4: Editorial Agent - Generation + Layout** - 에디토리얼 초안 생성 및 Magazine Layout JSON 구조화 출력
- [x] **Phase 5: Editorial Agent - DB Tools** - 셀럽/인플루언서 및 상품/브랜드 검색 Tool 스킬
- [x] **Phase 6: Review Agent + Feedback Loop** - LLM-as-a-Judge 품질 평가 및 반려 피드백 루프
- [x] **Phase 7: Admin Backend + HITL** - 콘텐츠 저장, 승인/반려 API, Human-in-the-loop interrupt 패턴
- [ ] **Phase 8: Admin Dashboard UI** - 콘텐츠 프리뷰 + 승인/반려 프론트엔드

## Phase Details

### Phase 1: Graph Skeleton + LLM Integration
**Goal**: 모든 에이전트의 기반이 되는 LangGraph StateGraph가 컴파일 가능하고, Gemini LLM 호출이 동작하는 상태
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02
**Success Criteria** (what must be TRUE):
  1. Python 프로젝트가 uv로 의존성 관리되고, `langgraph`, `langchain-google-genai` 패키지가 설치되어 import 가능하다
  2. StateGraph가 state schema, stub nodes, edges로 정의되어 `graph.compile()` 호출 시 에러 없이 컴파일된다
  3. `ChatGoogleGenerativeAI(model="gemini-2.5-flash")`로 프롬프트를 보내면 응답이 정상 반환된다
  4. LangSmith 트레이싱이 연결되어 그래프 실행 시 트레이스가 기록된다
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Python project scaffold (uv, pyproject.toml, src layout, pydantic-settings config)
- [x] 01-02-PLAN.md — LangGraph StateGraph skeleton (lean state schema, stub nodes, conditional edges, compile + tests)
- [x] 01-03-PLAN.md — Gemini LLM factory (create_llm, API call verification, LangSmith tracing)

### Phase 2: Data Layer
**Goal**: 파이프라인이 Supabase DB와 안정적으로 통신하고, 그래프 상태가 Postgres에 영속화되는 상태
**Depends on**: Phase 1
**Requirements**: FOUND-03, FOUND-04
**Success Criteria** (what must be TRUE):
  1. Supabase 서비스 레이어를 통해 셀럽, 상품, 포스트 데이터를 CRUD할 수 있다
  2. 서비스 레이어 함수들이 단위 테스트로 검증되어 있다
  3. `AsyncPostgresSaver` 체크포인터가 설정되어 그래프 실행 중단/재개 시 상태가 복원된다
  4. 체크포인터가 lean state 원칙을 따라 ID/참조만 저장하고 전체 페이로드는 Supabase에 저장된다
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Supabase service layer (config extension, client factory, Pydantic models, service functions, unit tests)
- [x] 02-02-PLAN.md — Postgres checkpointer setup (AsyncPostgresSaver factory, build_graph checkpointer param, MemorySaver tests, lean state validation)

### Phase 3: Curation Agent
**Goal**: 트리거 시 Perplexity API에서 패션 트렌드 키워드를 수집하여 파이프라인 상태로 전달하는 에이전트가 동작하는 상태
**Depends on**: Phase 1, Phase 2
**Requirements**: CURE-01, CURE-02
**Success Criteria** (what must be TRUE):
  1. Curation 노드 실행 시 Perplexity API를 호출하여 패션 트렌드 키워드 목록을 반환한다
  2. 수집된 키워드가 파이프라인 상태(`curated_topics`)에 구조화된 형태로 저장된다
  3. Perplexity API 실패 시 재시도 로직(exponential backoff)이 동작하고, 최종 실패 시 에러 상태가 기록된다
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Curation Pydantic models, prompt templates, CurationService (Gemini + Google Search Grounding, two-step pattern, retry logic)
- [x] 03-02-PLAN.md — Curation LangGraph node (state I/O, error handling) + graph wiring

### Phase 4: Editorial Agent - Generation + Layout
**Goal**: 큐레이션된 키워드와 수집 자료를 입력받아 Magazine Layout JSON 형식의 에디토리얼 초안을 생성하는 상태
**Depends on**: Phase 1, Phase 3
**Requirements**: EDIT-01, EDIT-04
**Success Criteria** (what must be TRUE):
  1. Editorial 노드에 키워드와 컨텍스트를 전달하면 에디토리얼 초안이 생성된다
  2. 생성된 초안이 Magazine Layout JSON Pydantic 스키마를 통과한다 (validation error 없음)
  3. Layout JSON에 타이틀, 본문 섹션, 이미지 플레이스홀더 등 에디토리얼에 필요한 구조가 포함된다
  4. Gemini structured output 실패 시 OutputFixingParser가 동작하여 복구를 시도한다
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md — Magazine Layout JSON Pydantic schema (block types, versioning, editorial content model, default template, tests)
- [x] 04-02-PLAN.md — EditorialService (content generation, Nano Banana layout image, Vision AI parsing, output repair loop, template fallback, tests)
- [x] 04-03-PLAN.md — Editorial LangGraph node (state wiring, graph integration, replace stub_editorial)

### Phase 5: Editorial Agent - DB Tools
**Goal**: Editorial Agent가 Supabase에서 관련 셀럽/인플루언서와 상품/브랜드를 검색하여 초안에 반영하는 상태
**Depends on**: Phase 2, Phase 4
**Requirements**: EDIT-02, EDIT-03
**Success Criteria** (what must be TRUE):
  1. Editorial Agent가 키워드 기반으로 관련 셀럽/인플루언서를 Supabase에서 검색하여 초안에 포함시킨다
  2. Editorial Agent가 키워드 기반으로 관련 상품/브랜드를 Supabase에서 검색하여 초안에 포함시킨다
  3. Tool 호출 결과가 Layout JSON 내에 셀럽/상품 참조(ID 포함)로 구조화되어 있다
  4. DB에 매칭되는 셀럽/상품이 없을 때 graceful하게 처리된다 (에러 없이 빈 결과 반환)
**Plans**: 3 plans

Plans:
- [x] 05-01-PLAN.md — Multi-column OR search for celeb/product services + enrich prompts
- [x] 05-02-PLAN.md — Enrich service (keyword expansion, DB search orchestration, content re-generation, layout rebuild)
- [x] 05-03-PLAN.md — Enrich LangGraph node + graph wiring (editorial -> enrich -> review)

### Phase 6: Review Agent + Feedback Loop
**Goal**: 생성된 에디토리얼 초안을 자동 품질 평가하고, 실패 시 구조화된 피드백으로 재생성을 요청하며, 최대 재시도 제한이 동작하는 상태
**Depends on**: Phase 4
**Requirements**: REVW-01, REVW-02, REVW-03
**Success Criteria** (what must be TRUE):
  1. Review 노드가 에디토리얼 초안을 할루시네이션, 포맷, 팩트 기준으로 평가하여 pass/fail 결과를 반환한다
  2. 실패 시 구조화된 피드백(어떤 항목이 왜 실패했는지)이 Editorial Agent로 전달되어 재생성이 트리거된다
  3. 재시도 시 이전 피드백이 Editorial Agent에 주입되어 동일한 문제가 반복되지 않는 방향으로 개선된다
  4. 최대 3회 재시도 후에도 실패 시 에스컬레이션 상태로 전환되어 무한 루프가 발생하지 않는다
  5. Review -> Editorial 피드백 루프가 LangGraph conditional edge로 구현되어 그래프 토폴로지에서 확인 가능하다
**Plans**: 3 plans

Plans:
- [x] 06-01-PLAN.md — Review models, prompt, and service (hybrid Pydantic+LLM evaluation)
- [x] 06-02-PLAN.md — Structured feedback schema + Editorial Agent feedback injection
- [x] 06-03-PLAN.md — Review node + graph wiring (review_node replaces stub_review, conditional edge loop)

### Phase 7: Admin Backend + HITL
**Goal**: 검수 통과 콘텐츠가 Supabase에 저장되고, 관리자가 API로 승인/반려할 수 있으며, 파이프라인이 승인 대기 중 일시정지되는 상태
**Depends on**: Phase 2, Phase 6
**Requirements**: ADMN-01, ADMN-02, ADMN-03
**Success Criteria** (what must be TRUE):
  1. 검수 통과된 콘텐츠가 Supabase에 pending 상태로 자동 저장된다
  2. FastAPI 엔드포인트로 pending 콘텐츠 목록 조회, 개별 콘텐츠 상세 조회가 가능하다
  3. 승인/반려 API 호출 시 콘텐츠 상태가 변경되고, 승인 시 발행 파이프라인이 재개된다
  4. `interrupt()` 패턴으로 파이프라인이 Admin Gate에서 일시정지되고, `Command(resume=...)` 호출 시 정확히 이어서 실행된다
  5. 서버 재시작 후에도 대기 중인 파이프라인이 Postgres 체크포인터를 통해 복원된다
**Plans**: 3 plans

Plans:
- [x] 07-01-PLAN.md — Content service + admin_gate node (interrupt pattern, content snapshot to Supabase) + publish node
- [x] 07-02-PLAN.md — FastAPI admin API (app scaffold, content list/detail, approve/reject, pipeline trigger endpoints)
- [x] 07-03-PLAN.md — Graph wiring + interrupt/resume integration tests (replace stubs, end-to-end flow)

### Phase 8: Admin Dashboard UI
**Goal**: 관리자가 웹 브라우저에서 콘텐츠를 프리뷰하고 승인/반려할 수 있는 대시보드가 동작하는 상태
**Depends on**: Phase 7
**Requirements**: ADMN-04
**Success Criteria** (what must be TRUE):
  1. 웹 브라우저에서 pending 콘텐츠 목록을 확인할 수 있다
  2. 개별 콘텐츠의 Magazine Layout JSON이 프리뷰로 렌더링되어 실제 출력 형태를 확인할 수 있다
  3. 승인/반려 버튼 클릭으로 콘텐츠 상태를 변경할 수 있고, 결과가 즉시 반영된다
  4. 반려 시 사유를 입력할 수 있다
**Plans**: TBD

Plans:
- [ ] 08-01: Dashboard scaffold (tech stack selection, project setup, routing)
- [ ] 08-02: Content list + preview page (Layout JSON rendering)
- [ ] 08-03: Approve/reject flow (API integration, status feedback, rejection reason)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Graph Skeleton + LLM Integration | 3/3 | Complete | 2026-02-25 |
| 2. Data Layer | 2/2 | Complete | 2026-02-25 |
| 3. Curation Agent | 2/2 | Complete | 2026-02-25 |
| 4. Editorial Agent - Generation + Layout | 3/3 | Complete | 2026-02-25 |
| 5. Editorial Agent - DB Tools | 3/3 | Complete | 2026-02-25 |
| 6. Review Agent + Feedback Loop | 3/3 | Complete | 2026-02-25 |
| 7. Admin Backend + HITL | 3/3 | Complete | 2026-02-25 |
| 8. Admin Dashboard UI | 0/3 | Not started | - |
