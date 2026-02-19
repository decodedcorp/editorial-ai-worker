# Editorial AI Worker

## What This Is

패션 에디토리얼 콘텐츠를 자동으로 기획, 집필, 검수, 발행하는 멀티 에이전트 AI 파이프라인. 트렌드 키워드 큐레이션부터 매거진 레이아웃 JSON 생성, 품질 검수, 관리자 승인까지 End-to-End로 처리한다. 초기에는 패션 도메인에 집중하고 라이프스타일 전반으로 확장 예정.

## Core Value

키워드 하나로 셀럽/상품/레퍼런스가 조합된 에디토리얼 콘텐츠가 자동 생성되고, 검수 루프를 거쳐 관리자가 승인하면 바로 발행될 수 있어야 한다.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Curation Agent: Perplexity API로 트렌드 키워드 자동 수집
- [ ] Curation Agent: 키워드 기반 Vector DB 검색으로 관련 과거 포스트 조회
- [ ] Editorial Agent: 키워드 + 수집 자료 기반 에디토리얼 초안 자동 생성
- [ ] Editorial Skill: Supabase에서 관련 셀럽/인플루언서 검색
- [ ] Editorial Skill: Supabase에서 관련 상품/브랜드 검색
- [ ] Editorial Skill: 외부 레퍼런스(이미지, 아티클) 수집
- [ ] Editorial Skill: SNS 콘텐츠(인스타, 유튜브) 링크 수집
- [ ] Editorial Skill: 프론트엔드 렌더링용 Magazine Layout JSON 구조화 출력
- [ ] Source Agent: Perplexity 기반 심층 출처 탐색 (URL, 팩트 검증)
- [ ] 검수 Agent: LLM-as-a-Judge 기반 품질 평가 (할루시네이션, 포맷, 팩트 체크)
- [ ] 검수 Agent: 실패 시 구체적 피드백과 함께 Editorial Agent로 반려 (피드백 루프)
- [ ] Admin API: 검수 통과 콘텐츠를 Supabase에 pending 상태로 저장
- [ ] Admin 대시보드: 콘텐츠 프리뷰 + 승인/반려 UI
- [ ] Human-in-the-loop: 관리자 승인 시 발행 파이프라인 재개
- [ ] 주간 자동 실행: Cloud Scheduler/Cron 기반 Curation 트리거

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
*Last updated: 2026-02-20 after initialization*
