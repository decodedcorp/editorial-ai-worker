# Roadmap: Editorial AI Worker

## Milestones

- v1.0 MVP 파이프라인 구축 (Phases 1-8) -- shipped 2026-02-26
- v1.1 파이프라인 실행 검증 + 관측성 + 매거진 렌더러 (Phases 9-13) -- in progress

## Phases

<details>
<summary>v1.0 MVP 파이프라인 구축 (Phases 1-8) - SHIPPED 2026-02-26</summary>

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
**Plans**: 3 plans

Plans:
- [x] 08-01-PLAN.md — Dashboard scaffold (tech stack selection, project setup, routing)
- [x] 08-02-PLAN.md — Content list + preview page (Layout JSON rendering)
- [x] 08-03-PLAN.md — Approve/reject flow (API integration, status feedback, rejection reason)

</details>

### v1.1 파이프라인 실행 검증 + 관측성 + 매거진 렌더러 (In Progress)

**Milestone Goal:** v1.0 파이프라인을 실제 환경에서 실행 검증하고, 노드별 상세 로그를 수집하여 Admin에 표시하며, Layout JSON을 실제 매거진 형태로 렌더링한다.

- [x] **Phase 9: E2E Execution Foundation** - 실제 환경에서 파이프라인이 처음부터 끝까지 동작하는 상태 확보
- [x] **Phase 10: Pipeline Observability Backend** - 노드별 실행 메트릭 수집, 저장, API 제공
- [x] **Phase 11: Magazine Renderer Enhancement** - Layout JSON을 매거진 품질로 렌더링하는 블록 컴포넌트 고도화
- [ ] **Phase 12: Observability Dashboard** - Admin UI에 파이프라인 실행 로그와 진행 상태 표시
- [ ] **Phase 13: Pipeline Advanced** - 모델 라우팅, 컨텍스트 캐싱, 적응형 루브릭으로 파이프라인 고도화

## Phase Details (v1.1)

### Phase 9: E2E Execution Foundation
**Goal**: Admin UI에서 키워드를 입력하면 파이프라인이 실제 Gemini + Supabase 환경에서 처음부터 끝까지 정상 실행되는 상태
**Depends on**: Phase 8 (v1.0 complete)
**Requirements**: E2E-01, E2E-02, E2E-03, E2E-04, E2E-05
**Success Criteria** (what must be TRUE):
  1. 필수 환경변수가 누락된 상태로 서버를 시작하면 어떤 변수가 빠졌는지 명확한 에러 메시지와 함께 즉시 종료된다
  2. GET /health 호출 시 Supabase 연결, 테이블 존재, 체크포인터 연결 상태가 JSON으로 반환된다
  3. Admin 대시보드에서 '새 콘텐츠 생성' 버튼을 클릭하고 키워드를 입력하면 파이프라인이 트리거되어 pending 콘텐츠가 생성된다
  4. 셀럽/상품 샘플 데이터가 SQL 스크립트로 제공되어, 빈 DB에서도 파이프라인이 유의미한 콘텐츠를 생성한다
  5. seed_keyword 필드명 불일치가 해소되어 curation 노드가 키워드를 정상적으로 수신한다
**Plans**: 3 plans

Plans:
- [x] 09-01-PLAN.md — Backend prerequisites (seed_keyword fix, env validation, rich health check)
- [x] 09-02-PLAN.md — Sample data SQL seed script (posts, spots, solutions, celebs, products)
- [x] 09-03-PLAN.md — Content creation trigger UI (modal, progress polling, pipeline status endpoint)

### Phase 10: Pipeline Observability Backend
**Goal**: 파이프라인 실행 시 각 노드의 토큰 사용량, 처리 시간, 상태가 자동 수집되어 API로 조회 가능한 상태
**Depends on**: Phase 9
**Requirements**: OBS-01, OBS-02, OBS-03
**Success Criteria** (what must be TRUE):
  1. 파이프라인을 실행하면 7개 노드 각각의 실행 시간(ms), 토큰 사용량, 성공/실패 상태가 pipeline_node_runs 테이블에 자동 저장된다
  2. GET /api/contents/{id}/logs 호출 시 해당 콘텐츠의 노드별 실행 로그가 시간순으로 반환된다
  3. 관측성 수집이 실패해도 파이프라인 실행은 중단되지 않는다 (fire-and-forget)
  4. 관측성 데이터가 EditorialPipelineState가 아닌 별도 저장소(로컬 JSONL)에 저장되어 기존 체크포인트와 충돌하지 않는다
**Plans**: 3 plans

Plans:
- [x] 10-01-PLAN.md — Observability models, token collector context var, JSONL storage
- [x] 10-02-PLAN.md — Node wrapper decorator, service layer token injection, graph wiring
- [x] 10-03-PLAN.md — Logs API endpoint (GET /api/contents/{id}/logs)

### Phase 11: Magazine Renderer Enhancement
**Goal**: Admin 상세 페이지의 매거진 프리뷰가 실제 이미지, 에디토리얼 타이포그래피, 에러 복원력을 갖춘 매거진 품질로 렌더링되는 상태
**Depends on**: Phase 8 (existing block components)
**Requirements**: MAG-01, MAG-02, MAG-03, MAG-04
**Success Criteria** (what must be TRUE):
  1. hero, product, celeb, gallery 블록에서 이미지 URL이 실제 이미지로 렌더링되고, 로드 실패 시 fallback 이미지가 표시된다
  2. 본문 텍스트가 세리프 폰트, 드롭캡, 적절한 행간으로 매거진 느낌의 타이포그래피를 갖춘다
  3. 개별 블록의 데이터가 malformed여도 해당 블록만 에러 표시되고 나머지 페이지는 정상 렌더링된다
  4. 상세 페이지에서 JSON 원본과 렌더링된 매거진 뷰를 나란히(side-by-side) 비교할 수 있다
**Plans**: 4 plans

Plans:
- [x] 11-01-PLAN.md — DesignSpec pipeline node (Pydantic model, Gemini service, graph wiring)
- [x] 11-02-PLAN.md — MagazineImage + BlockErrorBoundary (progressive loading, gradient fallback, per-block error isolation)
- [x] 11-03-PLAN.md — Block components upgrade (10 blocks: real images, magazine typography, Google Fonts, design spec)
- [x] 11-04-PLAN.md — Detail page tab integration (Magazine/JSON tabs, DesignSpec context provider)

### Phase 12: Observability Dashboard
**Goal**: Admin 대시보드에서 파이프라인 실행 과정을 시각적으로 추적하고 비용을 파악할 수 있는 상태
**Depends on**: Phase 10, Phase 11
**Requirements**: OBS-04, OBS-05, OBS-06
**Success Criteria** (what must be TRUE):
  1. 콘텐츠 상세 페이지에서 노드별 실행 타임라인(노드명, 소요시간, 성공/실패)을 시각적으로 확인할 수 있다
  2. 각 노드의 토큰 사용량과 예상 비용(Gemini 2.5 Flash 가격 기준)이 로그 패널에 표시된다
  3. 콘텐츠 목록 페이지에서 각 항목의 파이프라인 진행 상태(큐레이션 중/리뷰 중/승인 대기 중)를 한눈에 파악할 수 있다
**Plans**: TBD

### Phase 13: Pipeline Advanced
**Goal**: 파이프라인이 작업 복잡도에 따라 모델을 자동 선택하고, 반복 참조 소스를 캐싱하며, 콘텐츠 유형별 평가 기준을 동적 조정하는 상태
**Depends on**: Phase 9, Phase 10
**Requirements**: ADV-01, ADV-02, ADV-03
**Success Criteria** (what must be TRUE):
  1. 노드별 작업 복잡도에 따라 Gemini Pro/Flash/Flash-Lite 중 적절한 모델이 자동 선택되고, 선택 근거가 로그에 기록된다
  2. 동일 소스 문서를 참조하는 반복 실행에서 Vertex AI 컨텍스트 캐싱이 적용되어 토큰 비용이 절감된다
  3. 콘텐츠 유형(기술 블로그 vs 감성 매거진)에 따라 Review Agent의 평가 루브릭이 자동 조정된다
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 9 -> 10 -> 11 (parallelizable with 10) -> 12 -> 13

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Graph Skeleton + LLM Integration | v1.0 | 3/3 | Complete | 2026-02-25 |
| 2. Data Layer | v1.0 | 2/2 | Complete | 2026-02-25 |
| 3. Curation Agent | v1.0 | 2/2 | Complete | 2026-02-25 |
| 4. Editorial Agent - Generation + Layout | v1.0 | 3/3 | Complete | 2026-02-25 |
| 5. Editorial Agent - DB Tools | v1.0 | 3/3 | Complete | 2026-02-25 |
| 6. Review Agent + Feedback Loop | v1.0 | 3/3 | Complete | 2026-02-25 |
| 7. Admin Backend + HITL | v1.0 | 3/3 | Complete | 2026-02-25 |
| 8. Admin Dashboard UI | v1.0 | 3/3 | Complete | 2026-02-26 |
| 9. E2E Execution Foundation | v1.1 | 3/3 | Complete | 2026-02-26 |
| 10. Pipeline Observability Backend | v1.1 | 3/3 | Complete | 2026-02-26 |
| 11. Magazine Renderer Enhancement | v1.1 | 4/4 | Complete | 2026-02-26 |
| 12. Observability Dashboard | v1.1 | 0/TBD | Not started | - |
| 13. Pipeline Advanced | v1.1 | 0/TBD | Not started | - |
