# Requirements: Editorial AI Worker

**Defined:** 2026-02-20
**Core Value:** 키워드 하나로 셀럽/상품/레퍼런스가 조합된 에디토리얼 콘텐츠가 자동 생성되고, 검수 루프를 거쳐 관리자가 승인하면 발행

## v1.0 Requirements (Complete)

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

- [x] **ADMN-01**: 검수 통과 콘텐츠를 Supabase에 pending 상태로 저장
- [x] **ADMN-02**: 콘텐츠 프리뷰 + 승인/반려 API
- [x] **ADMN-03**: Human-in-the-loop: interrupt() 패턴으로 관리자 승인 대기
- [x] **ADMN-04**: 간단한 Admin 대시보드 UI (프리뷰 + 승인/반려)

## v1.1 Requirements (파이프라인 실행 검증 + 관측성 + 매거진 렌더러)

### E2E 실행 환경

- [ ] **E2E-01**: 필수 환경변수(GOOGLE_API_KEY, SUPABASE_URL 등) 누락 시 시작 단계에서 명확한 에러와 함께 fail-fast
- [ ] **E2E-02**: GET /health 엔드포인트로 Supabase 연결 + 테이블 존재 + 체크포인터 연결 검증
- [ ] **E2E-03**: curation_input seed_keyword/keyword 필드명 불일치 수정
- [ ] **E2E-04**: Admin 대시보드에 '새 콘텐츠 생성' 버튼 + 키워드 입력 폼 (파이프라인 트리거)
- [ ] **E2E-05**: 셀럽/상품 샘플 데이터 SQL seed 스크립트

### 파이프라인 관측성

- [ ] **OBS-01**: 각 노드별 실행 로그 수집 (토큰 사용량, 처리 시간, 프롬프트, 입력 데이터) — node_wrapper 데코레이터 패턴
- [ ] **OBS-02**: pipeline_node_runs Supabase 테이블 + 마이그레이션 SQL
- [ ] **OBS-03**: 파이프라인 로그 API 엔드포인트 (GET /api/contents/{id}/logs)
- [ ] **OBS-04**: Admin 상세 페이지에 노드별 타임라인 로그 패널 (토큰/시간/프롬프트 확인)
- [ ] **OBS-05**: 토큰 비용 추정 표시 (Gemini 2.5 Flash 가격 기반 "이 실행 비용: ~$0.03")
- [ ] **OBS-06**: 콘텐츠 목록 페이지에 파이프라인 진행 상태 표시 (큐레이션 중/리뷰 중/대기 중)

### 매거진 렌더러

- [ ] **MAG-01**: 4개 이미지 블록(hero, product, celeb, gallery) 플레이스홀더 → 실제 이미지 렌더링 + fallback
- [ ] **MAG-02**: 매거진 품질 타이포그래피 (세리프 본문, 드롭캡, 적절한 line-height, Google Fonts)
- [ ] **MAG-03**: 블록 레벨 에러 바운더리 (malformed 데이터로 전체 페이지 크래시 방지)
- [ ] **MAG-04**: 상세 페이지 JSON + 렌더링 병렬(side-by-side) 뷰

### 파이프라인 고도화

- [ ] **ADV-01**: 다이나믹 모델 라우팅 — 작업 복잡도에 따라 Gemini Pro/Flash/Flash-Lite 자동 선택
- [ ] **ADV-02**: 컨텍스트 캐싱 — 반복 참조 소스 문서에 대한 Vertex AI 캐싱 적용으로 비용/지연 절감
- [ ] **ADV-03**: 적응형 루브릭 — 콘텐츠 유형별(기술 블로그/감성 매거진) 동적 평가 기준 조정

## Future Requirements

### Curation Enhancement

- **CURE-03**: Vector DB 기반 과거 포스트 유사도 검색 (중복 방지)
- **CURE-04**: 주간 Cron 자동 트리거 (Cloud Scheduler)
- **CURE-05**: 배치 생성 (복수 토픽 동시 처리)

### Editorial Enhancement

- **EDIT-05**: Source Agent — Perplexity 기반 심층 출처 탐색 (URL, 팩트 검증)
- **EDIT-06**: SNS 콘텐츠 수집 (인스타, 유튜브 링크)
- **EDIT-07**: 외부 레퍼런스 (이미지, 아티클) 수집
- **EDIT-08**: 다중 에디토리얼 템플릿 지원

### Operations

- **OPS-02**: Cloud Run 배포
- **OPS-03**: 품질 분석 대시보드
- **SSE-01**: 실시간 파이프라인 진행 표시 (Server-Sent Events)
- **MAG-05**: 매거진 테마 시스템 (CSS variables)
- **MAG-06**: 매거진 PDF 내보내기

## Out of Scope

| Feature | Reason |
|---------|--------|
| 프론트엔드 매거진 뷰어 (threejs/gsap) | decoded-app 레포에서 별도 구현 |
| 사용자 인증/계정 시스템 | Supabase auth + decoded-app에서 처리 |
| AI 이미지 생성 | 패션은 실제 사진 사용, 생성 이미지는 uncanny valley + 저작권 문제 |
| 실시간 생성 (on-demand) | 에디토리얼은 배치 생성 + 비동기 검수 구조 |
| WYSIWYG 에디터 / 블록 인라인 편집 | Admin은 승인/반려만, 편집은 AI 재생성으로 |
| 다국어 지원 | 초기 한국어 전용 |
| 영상 콘텐츠 생성 | 텍스트 + 이미지 레이아웃에 집중 |
| LLM 파인튜닝 | 프롬프트 엔지니어링 + few-shot으로 충분 |
| Langfuse/OpenTelemetry 풀스택 | 커스텀 경량 로깅으로 충분, 규모 확대 시 검토 |
| 프롬프트 플레이그라운드 | 코드에서 프롬프트 엔지니어링 수행 |
| 파이프라인 비교 뷰 (A/B) | 다수 실행 데이터 축적 후 검토 |

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
| ADMN-01 | Phase 7 | Complete |
| ADMN-02 | Phase 7 | Complete |
| ADMN-03 | Phase 7 | Complete |
| ADMN-04 | Phase 8 | Complete |
| E2E-01 | Phase 9 | Pending |
| E2E-02 | Phase 9 | Pending |
| E2E-03 | Phase 9 | Pending |
| E2E-04 | Phase 9 | Pending |
| E2E-05 | Phase 9 | Pending |
| OBS-01 | Phase 10 | Pending |
| OBS-02 | Phase 10 | Pending |
| OBS-03 | Phase 10 | Pending |
| OBS-04 | Phase 12 | Pending |
| OBS-05 | Phase 12 | Pending |
| OBS-06 | Phase 12 | Pending |
| MAG-01 | Phase 11 | Pending |
| MAG-02 | Phase 11 | Pending |
| MAG-03 | Phase 11 | Pending |
| MAG-04 | Phase 11 | Pending |
| ADV-01 | Phase 13 | Pending |
| ADV-02 | Phase 13 | Pending |
| ADV-03 | Phase 13 | Pending |

**Coverage:**
- v1.0 requirements: 17 total (all complete)
- v1.1 requirements: 18 total
- Mapped to phases: 18/18
- Unmapped: 0

---
*Requirements defined: 2026-02-20*
*Last updated: 2026-02-26 after v1.1 roadmap creation*
