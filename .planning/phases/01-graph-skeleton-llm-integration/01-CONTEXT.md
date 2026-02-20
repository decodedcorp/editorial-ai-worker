# Phase 1: Graph Skeleton + LLM Integration - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

LangGraph StateGraph 스켈레톤과 Vertex AI(Gemini) 연동. Python 프로젝트 scaffold, 그래프 컴파일, LLM 호출 동작 확인까지. 모든 후속 Phase의 기반이 되는 인프라 레이어.

</domain>

<decisions>
## Implementation Decisions

### 파이프라인 상태 설계
- Claude's Discretion: Lean state vs full state 결정
- Claude's Discretion: 피드백 히스토리 누적 방식 (Annotated reducer vs last-write-wins)
- 리서치에서 lean state (ID/참조만) + Annotated reducer (피드백 로그)를 권장했으므로 이를 기본으로 검토

### 그래프 토폴로지
- Claude's Discretion: Editorial Agent 단일 노드 vs 서브그래프 (리서치 권장: 단일 노드로 시작)
- Claude's Discretion: 실패 처리 전략 (토픽별 격리 vs 전체 중단)
- 전체 토폴로지: Curation → Editorial(+Tools) → Source → Review(→피드백 루프) → Admin Gate → Publish
- stub nodes로 시작하여 Phase별로 실제 구현 교체

### 프로젝트 구조
- Claude's Discretion: 폴더 구조 (도메인별 vs 기능별 — 리서치에서 명확한 권장 없음)
- Python 프로젝트, uv 패키지 매니저 사용
- Admin Dashboard UI는 **Next.js**로 구현 (decoded-app과 동일 스택)

### Gemini 모델 선택
- Vertex AI 선택 이유: Google 울트라 요금제 활용 + Tool Calling 연동 편의성
- `ChatGoogleGenerativeAI` 사용 (deprecated `ChatVertexAI` 아님 — 리서치에서 확인)
- 에이전트별 모델 분리: 초기에는 단일 모델로 시작, 이후 검증하며 최적화 (Editorial=Pro, Review=Flash 등)
- Gemini 2.5 Flash를 기본 모델로 시작 (리서치 권장)

### Claude's Discretion
- State schema 세부 설계 (TypedDict 필드 구성)
- 노드 간 데이터 흐름 세부 패턴
- 프로젝트 폴더 구조 및 모듈 분리
- LangSmith 트레이싱 설정 세부사항
- 에러 핸들링 패턴

</decisions>

<specifics>
## Specific Ideas

- Vertex AI를 통한 skill/tool 연결이 용이한 구조로 설계
- Google 울트라 요금제 내에서 API 호출 — 비용 구조 확인 필요
- 리서치에서 경고: `langchain-google-vertexai` 패키지가 2026.06 지원 중단 예정, `langchain-google-genai>=4.1.2` 사용 필수
- 리서치에서 경고: checkpoint state bloat 방지를 위해 lean state 원칙을 graph skeleton 단계에서 확립

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-graph-skeleton-llm-integration*
*Context gathered: 2026-02-20*
