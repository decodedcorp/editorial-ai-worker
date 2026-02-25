# Requirements: Editorial AI Worker

**Defined:** 2026-02-20
**Core Value:** 키워드 하나로 셀럽/상품/레퍼런스가 조합된 에디토리얼 콘텐츠가 자동 생성되고, 검수 루프를 거쳐 관리자가 승인하면 발행

## v1 Requirements (MVP)

### Foundation

- [x] **FOUND-01**: LangGraph StateGraph 기반 파이프라인 스켈레톤 구축 (state schema, nodes, edges)
- [x] **FOUND-02**: Vertex AI (ChatGoogleGenerativeAI) 연동 및 기본 LLM 호출
- [x] **FOUND-03**: Supabase 서비스 레이어 (셀럽, 상품, 포스트 CRUD)
- [x] **FOUND-04**: LangGraph 체크포인터 설정 (Postgres 기반 상태 영속화)

### Curation

- [x] **CURE-01**: Perplexity API로 패션 트렌드 키워드 자동 수집
- [x] **CURE-02**: 수집된 키워드를 파이프라인 상태에 전달

### Editorial

- [x] **EDIT-01**: 키워드 + 수집 자료 기반 에디토리얼 초안 자동 생성
- [x] **EDIT-02**: Supabase에서 관련 셀럽/인플루언서 검색 (Tool/Skill)
- [x] **EDIT-03**: Supabase에서 관련 상품/브랜드 검색 (Tool/Skill)
- [x] **EDIT-04**: Magazine Layout JSON 구조화 출력 (Structured Output)

### Review

- [x] **REVW-01**: LLM-as-a-Judge 기반 품질 평가 (할루시네이션, 포맷, 팩트)
- [x] **REVW-02**: 실패 시 구조화된 피드백과 함께 Editorial Agent로 반려
- [x] **REVW-03**: 최대 3회 재시도 제한, 초과 시 에스컬레이션

### Admin

- [ ] **ADMN-01**: 검수 통과 콘텐츠를 Supabase에 pending 상태로 저장
- [ ] **ADMN-02**: 콘텐츠 프리뷰 + 승인/반려 API
- [ ] **ADMN-03**: Human-in-the-loop: interrupt() 패턴으로 관리자 승인 대기
- [ ] **ADMN-04**: 간단한 Admin 대시보드 UI (프리뷰 + 승인/반려)

## v2 Requirements

### Curation Enhancement

- **CURE-03**: Vector DB 기반 과거 포스트 유사도 검색 (중복 방지)
- **CURE-04**: 주간 Cron 자동 트리거 (Cloud Scheduler)
- **CURE-05**: 배치 생성 (복수 토픽 동시 처리)

### Editorial Enhancement

- **EDIT-05**: Source Agent — Perplexity 기반 심층 출처 탐색 (URL, 팩트 검증)
- **EDIT-06**: SNS 콘텐츠 수집 (인스타, 유튜브 링크)
- **EDIT-07**: 외부 레퍼런스 (이미지, 아티클) 수집
- **EDIT-08**: 다중 에디토리얼 템플릿 지원

### Review Enhancement

- **REVW-04**: 다차원 점수 평가 (할루시네이션/톤/포맷/완성도 개별 점수)

### Operations

- **OPS-01**: 파이프라인 실행 로그/트레이싱 (LangSmith)
- **OPS-02**: Cloud Run 배포
- **OPS-03**: 품질 분석 대시보드

## Out of Scope

| Feature | Reason |
|---------|--------|
| 프론트엔드 매거진 뷰어 (threejs/gsap) | decoded-app 레포에서 별도 구현 |
| 사용자 인증/계정 시스템 | Supabase auth + decoded-app에서 처리 |
| AI 이미지 생성 | 패션은 실제 사진 사용, 생성 이미지는 uncanny valley + 저작권 문제 |
| 실시간 생성 (on-demand) | 에디토리얼은 배치 생성 + 비동기 검수 구조 |
| WYSIWYG 에디터 | Admin은 승인/반려만, 편집은 AI 재생성으로 |
| 다국어 지원 | 초기 한국어 전용 |
| 영상 콘텐츠 생성 | 텍스트 + 이미지 레이아웃에 집중 |
| LLM 파인튜닝 | 프롬프트 엔지니어링 + few-shot으로 충분, 데이터 축적 후 검토 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Complete |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 2 | Complete |
| FOUND-04 | Phase 2 | Complete |
| CURE-01 | Phase 3 | Complete |
| CURE-02 | Phase 3 | Complete |
| EDIT-01 | Phase 4 | Complete |
| EDIT-02 | Phase 5 | Complete |
| EDIT-03 | Phase 5 | Complete |
| EDIT-04 | Phase 4 | Complete |
| REVW-01 | Phase 6 | Complete |
| REVW-02 | Phase 6 | Complete |
| REVW-03 | Phase 6 | Complete |
| ADMN-01 | Phase 7 | Pending |
| ADMN-02 | Phase 7 | Pending |
| ADMN-03 | Phase 7 | Pending |
| ADMN-04 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---
*Requirements defined: 2026-02-20*
*Last updated: 2026-02-25 after Phase 6 completion*
