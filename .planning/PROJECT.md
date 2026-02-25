# Editorial AI Worker

## What This Is

패션 에디토리얼 콘텐츠를 자동으로 기획, 집필, 검수, 발행하는 멀티 에이전트 AI 파이프라인. 트렌드 키워드 큐레이션부터 매거진 레이아웃 JSON 생성, 품질 검수, 관리자 승인까지 End-to-End로 처리한다. 초기에는 패션 도메인에 집중하고 라이프스타일 전반으로 확장 예정.

## Core Value

키워드 하나로 셀럽/상품/레퍼런스가 조합된 에디토리얼 콘텐츠가 자동 생성되고, 검수 루프를 거쳐 관리자가 승인하면 바로 발행될 수 있어야 한다.

## Requirements

### Validated

<!-- v1.0 Milestone (Phase 1-8) — shipped 2026-02-26 -->

- ✓ LangGraph StateGraph 기반 파이프라인 스켈레톤 (state schema, nodes, edges) — Phase 1
- ✓ Vertex AI (Gemini 2.5 Flash) 연동 및 LLM 팩토리 — Phase 1
- ✓ Supabase 서비스 레이어 (셀럽, 상품, 포스트 CRUD) — Phase 2
- ✓ LangGraph Postgres 체크포인터 (상태 영속화) — Phase 2
- ✓ Gemini + Google Search Grounding 기반 트렌드 큐레이션 — Phase 3
- ✓ 에디토리얼 초안 자동 생성 + Magazine Layout JSON 구조화 출력 — Phase 4
- ✓ Supabase 셀럽/인플루언서 및 상품/브랜드 검색 Tool — Phase 5
- ✓ LLM-as-a-Judge 품질 평가 + 구조화된 피드백 반려 루프 (max 3회) — Phase 6
- ✓ Admin Backend + Human-in-the-loop interrupt 패턴 — Phase 7
- ✓ Admin Dashboard UI (콘텐츠 목록/프리뷰/승인/반려) — Phase 8

### Active

## Current Milestone: v1.1 파이프라인 실행 검증 + 관측성 + 매거진 렌더러

**Goal:** v1.0 파이프라인을 실제 환경에서 실행 검증하고, 노드별 상세 로그를 수집하여 Admin에 표시하며, Layout JSON을 실제 매거진 형태로 렌더링한다.

**Target features:**
- [ ] E2E 실행 환경 세팅 (환경변수, Supabase 연결, 실제 Gemini 호출)
- [ ] 파이프라인 관측성 — 각 노드별 상세 로그 (토큰, 시간, 입력 데이터, 프롬프트) 수집 및 저장
- [ ] Admin 상세 페이지에 파이프라인 실행 로그 표시
- [ ] Layout JSON → 동적 매거진 렌더러 (다채로운 레이아웃, 코드 컴포넌트 변환)

### Out of Scope

- 프론트엔드 매거진 뷰어 (threejs/gsap) — decoded-app 레포에서 별도 구현
- 사용자 인증/계정 시스템 — Supabase auth 이미 구축됨, decoded-app에서 처리
- 실시간 채팅/알림 — v1 범위 아님
- 다국어 지원 — 초기에는 한국어 전용
- 영상 콘텐츠 생성 — 텍스트 + 이미지 레이아웃에 집중

## Context

- **기존 인프라:** Supabase에 셀럽, 상품/브랜드, 과거 포스트 데이터 존재. Auth 구축 완료.
- **프론트엔드:** decoded-app (Next.js + Tailwind + Typesense) 별도 레포. 에디토리얼 콘텐츠는 Layout JSON으로 전달.
- **관리자 페이지:** 기존 프론트엔드에 어드민 페이지 존재. 이 레포에도 간단한 Admin 대시보드 포함하되 추후 마이그레이션 고려.
- **LangGraph + Vertex AI 처음 도입:** 팀에서 두 기술 모두 신규 도입. 학습 곡선 고려 필요.
- **아키텍처 다이어그램:** Curation → Editorial(5 Skills) → Source → 검수(피드백 루프) → Admin(Human-in-the-loop) → Publish

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
| LangGraph 선택 | 피드백 루프, 조건부 분기, Human-in-the-loop 등 복잡한 워크플로우 제어에 최적 | — Pending |
| Vertex AI (Gemini) 선택 | 긴 컨텍스트 윈도우로 다량의 DB 데이터 + Tool 호출 동시 처리 가능 | — Pending |
| Layout JSON 구조화 출력 | AI가 직접 프론트 코드를 짜는 대신 규격화된 JSON으로 출력하여 프론트 렌더링 분리 | — Pending |
| Admin을 이 레포에 포함 | 빠른 개발 + 추후 마이그레이션 염두 | — Pending |
| Python 선택 | LangGraph/Vertex AI 생태계가 Python 중심 | — Pending |

---
*Last updated: 2026-02-26 after v1.1 milestone start*
