# Editorial AI Worker

## What This Is

패션 에디토리얼 콘텐츠를 자동으로 기획, 집필, 검수, 발행하는 멀티 에이전트 AI 파이프라인. 트렌드 키워드 큐레이션부터 매거진 레이아웃 JSON 생성, 품질 검수, 관리자 승인까지 End-to-End로 처리한다. v1.1에서 실제 환경 실행 검증, 노드별 관측성, 매거진 품질 렌더러, 모델 라우팅/캐싱/적응형 루브릭까지 완성.

## Core Value

키워드 하나로 셀럽/상품/레퍼런스가 조합된 에디토리얼 콘텐츠가 자동 생성되고, 검수 루프를 거쳐 관리자가 승인하면 바로 발행될 수 있어야 한다.

## Requirements

### Validated

<!-- v1.0 Milestone (Phase 1-8) — shipped 2026-02-26 -->

- ✓ LangGraph StateGraph 기반 파이프라인 스켈레톤 (state schema, nodes, edges) — v1.0
- ✓ Vertex AI (Gemini 2.5 Flash) 연동 및 LLM 팩토리 — v1.0
- ✓ Supabase 서비스 레이어 (셀럽, 상품, 포스트 CRUD) — v1.0
- ✓ LangGraph Postgres 체크포인터 (상태 영속화) — v1.0
- ✓ Gemini + Google Search Grounding 기반 트렌드 큐레이션 — v1.0
- ✓ 에디토리얼 초안 자동 생성 + Magazine Layout JSON 구조화 출력 — v1.0
- ✓ Supabase 셀럽/인플루언서 및 상품/브랜드 검색 Tool — v1.0
- ✓ LLM-as-a-Judge 품질 평가 + 구조화된 피드백 반려 루프 (max 3회) — v1.0
- ✓ Admin Backend + Human-in-the-loop interrupt 패턴 — v1.0
- ✓ Admin Dashboard UI (콘텐츠 목록/프리뷰/승인/반려) — v1.0

<!-- v1.1 Milestone (Phase 9-13) — shipped 2026-02-26 -->

- ✓ E2E 실행 환경 (환경변수 fail-fast, health check, seed data, content creation trigger) — v1.1
- ✓ 파이프라인 관측성 백엔드 (노드별 토큰/시간 수집, JSONL 저장, 로그 API) — v1.1
- ✓ 매거진 렌더러 고도화 (AI 디자인 스펙, 프로그레시브 이미지, 에러 바운더리, 10 블록) — v1.1
- ✓ 관측성 대시보드 (Gantt 타임라인, 비용 추정, 목록 상태 표시) — v1.1
- ✓ Config-driven 모델 라우팅 (Flash-Lite/Flash/Pro 자동 선택) — v1.1
- ✓ 컨텍스트 캐싱 (retry 경로 토큰 비용 절감) — v1.1
- ✓ 적응형 루브릭 (콘텐츠 유형별 동적 평가 기준) — v1.1

### Active

(Next milestone — run `/gsd:new-milestone` to define)

### Out of Scope

- 프론트엔드 매거진 뷰어 (threejs/gsap) — decoded-app 레포에서 별도 구현
- 사용자 인증/계정 시스템 — Supabase auth 이미 구축됨, decoded-app에서 처리
- AI 이미지 생성 — 패션은 실제 사진 사용, 생성 이미지는 uncanny valley + 저작권 문제
- 실시간 생성 (on-demand) — 에디토리얼은 배치 생성 + 비동기 검수 구조
- WYSIWYG 에디터 / 블록 인라인 편집 — Admin은 승인/반려만, 편집은 AI 재생성으로
- 다국어 지원 — 초기 한국어 전용
- 영상 콘텐츠 생성 — 텍스트 + 이미지 레이아웃에 집중
- LLM 파인튜닝 — 프롬프트 엔지니어링 + few-shot으로 충분
- Langfuse/OpenTelemetry 풀스택 — 커스텀 경량 로깅으로 충분, 규모 확대 시 검토
- 프롬프트 플레이그라운드 — 코드에서 프롬프트 엔지니어링 수행
- 파이프라인 비교 뷰 (A/B) — 다수 실행 데이터 축적 후 검토

## Context

- **Shipped:** v1.0 MVP (8 phases, 22 plans) + v1.1 (5 phases, 16 plans) = 13 phases, 38 plans
- **Codebase:** ~5,822 LOC Python + ~4,276 LOC TypeScript
- **Tech stack:** Python + LangGraph + Gemini (google-genai SDK) + Supabase + FastAPI + Next.js 15
- **기존 인프라:** Supabase에 셀럽, 상품/브랜드, 과거 포스트 데이터 존재. Auth 구축 완료.
- **프론트엔드:** decoded-app (Next.js + Tailwind + Typesense) 별도 레포
- **Known tech debt:** 8 items from v1.1 audit (see milestones/v1.1-ROADMAP.md)

## Constraints

- **Tech Stack**: Python + LangGraph + Vertex AI (Gemini) — 멀티 에이전트 오케스트레이션에 최적
- **Database**: Supabase (PostgreSQL) — 기존 인프라 활용
- **Vector DB**: 신규 구축 필요 — 과거 포스트 임베딩 저장용
- **External API**: Perplexity API — 트렌드 검색 및 출처 탐색
- **Output Format**: Magazine Layout JSON — decoded-app 프론트엔드가 소비할 수 있는 구조화된 포맷
- **Admin UI**: 이 레포에 포함하되 추후 마이그레이션 용이하도록 API 분리 설계

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LangGraph 선택 | 피드백 루프, 조건부 분기, Human-in-the-loop 등 복잡한 워크플로우 제어에 최적 | ✓ Good — 7개 노드 + 조건부 엣지 파이프라인 안정적 운영 |
| Vertex AI (Gemini) 선택 | 긴 컨텍스트 윈도우로 다량의 DB 데이터 + Tool 호출 동시 처리 가능 | ✓ Good — Flash/Pro 모델 라우팅까지 활용 |
| Layout JSON 구조화 출력 | AI가 직접 프론트 코드를 짜는 대신 규격화된 JSON으로 출력하여 프론트 렌더링 분리 | ✓ Good — 10 블록 타입, 매거진 품질 렌더링 달성 |
| Admin을 이 레포에 포함 | 빠른 개발 + 추후 마이그레이션 염두 | ✓ Good — BFF 패턴으로 API 분리 유지 |
| Python 선택 | LangGraph/Vertex AI 생태계가 Python 중심 | ✓ Good |
| 커스텀 node_wrapper 관측성 | google-genai SDK 직접 사용으로 LangChain callbacks 불가 | ✓ Good — ContextVar 패턴으로 10개 호출 지점 계측 |
| YAML config-driven 모델 라우팅 | 코드 변경 없이 모델 매핑 튜닝 | ✓ Good — 운영 유연성 확보 |
| Fire-and-forget 관측성/캐싱 | 관측성/캐싱 실패가 파이프라인을 중단시키지 않도록 | ✓ Good — 안정성 확보 |

---
*Last updated: 2026-02-26 after v1.1 milestone*
