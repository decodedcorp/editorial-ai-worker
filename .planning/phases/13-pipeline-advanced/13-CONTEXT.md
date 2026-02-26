# Phase 13: Pipeline Advanced - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

파이프라인이 작업 복잡도에 따라 모델을 자동 선택하고, 반복 참조 소스를 캐싱하며, 콘텐츠 유형별 평가 기준을 동적 조정하는 상태. 새로운 파이프라인 노드나 Admin UI 기능 추가는 범위 밖.

</domain>

<decisions>
## Implementation Decisions

### 모델 라우팅 전략
- 하이브리드 방식: 노드별 기본 모델 고정 매핑 + 특정 조건(재시도, 긴 입력 등)에서 상위 모델로 업그레이드
- 모델 풀 구성: **리서처 조사 필요** — Gemini 모델 간 토큰 비용/품질 비교 후 결정 (Pro/Flash/Flash-Lite 조합)
- 설정 관리: Config 파일(YAML/JSON)로 노드-모델 매핑 정의. Admin UI에서 수정 불필요
- 라우팅 결정 로깅: Claude 재량으로 관측성 로그에 모델 선택 정보 포함

### 컨텍스트 캐싱
- 캐싱 대상: **리서처 분석 필요** — 실제 토큰 사용량 데이터 기반으로 캐싱 효과가 큰 소스 식별
- SDK 전환: Vertex AI 전환 OK (현재 google-genai에서 Vertex AI SDK로 전환 허용)
- 캐시 수명/무효화 정책: Claude 재량
- 비용 추적/표시: Claude 재량

### 적응형 루브릭
- 콘텐츠 유형 분류: 입력 키워드 기반 자동 분류 (키워드 도메인으로 콘텐츠 유형 판단)
- 유형별 평가 기준 차이: Claude 재량 (기술 블로그 vs 감성 매거진 등 유형별 최적 기준 설계)
- 루브릭 조정 시점: Claude 재량
- 새 유형 확장 방식: Claude 재량

### Claude's Discretion
- 모델 라우팅 로깅 수준 (model_used만 vs routing_reason 포함)
- 컨텍스트 캐시 수명 정책 (TTL vs 변경 감지)
- 캐싱 비용 절감 추적/표시 수준
- 적응형 루브릭의 구체적 평가 항목 및 가중치
- 루브릭 조정 시점 (파이프라인 시작 vs 리뷰 노드 진입)
- 새 콘텐츠 유형 확장 아키텍처 (config vs code)

</decisions>

<specifics>
## Specific Ideas

- 모델 풀 결정 전 리서처가 Gemini 모델 간 토큰 비용/출력 품질을 비교 분석해야 함
- 캐싱 대상 결정 전 리서처가 현재 파이프라인의 실제 반복 패턴과 토큰 사용량을 분석해야 함
- Vertex AI 전환 시 기존 google-genai 기반 코드와의 호환성 조사 필요

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-pipeline-advanced*
*Context gathered: 2026-02-26*
