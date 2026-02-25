# Phase 3: Curation Agent - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

트리거 시 패션 트렌드 키워드를 수집하여 파이프라인 상태(`curated_topics`)로 전달하는 에이전트. 시드 키워드를 입력받아 Gemini + Google Search Grounding으로 트렌드 데이터를 수집하고, 여러 서브 토픽으로 확장하여 구조화된 형태로 저장한다. 에디토리얼 초안 생성(Phase 4)과 DB 매칭(Phase 5)은 이 Phase의 범위 밖이다.

</domain>

<decisions>
## Implementation Decisions

### Trigger input & prompt design
- 관리자가 단일 시드 키워드를 입력하여 Curation 시작 (e.g., 'Y2K', '리넨 패션', '2026 S/S')
- **Perplexity API 대신 Gemini + Google Search Grounding 사용** (테스트 검증 완료 — 최신 트렌드, 한국 소스, 셀럽/브랜드 메타데이터 충분히 수집 가능)
- 수집 방향: 트렌드 배경 리서치 + 연관 키워드 + 셀럽 + 브랜드 + 시즌성
- 언어/지역 포커스: 글로벌 + 한국 혼합 (한국 셀럽/브랜드 포함하되 글로벌 트렌드 기반)

### Keyword output structure
- 테스트에서 검증된 JSON 구조 그대로 사용:
  - `keyword`: 시드 키워드
  - `trend_background`: 트렌드 배경 설명
  - `related_keywords`: 연관 키워드 목록
  - `celebrities`: [{name, relevance}] 관련 셀럽/인플루언서
  - `brands_products`: [{name, relevance}] 관련 브랜드/상품
  - `seasonality`: 시즌/시기 관련성
  - `sources`: Grounding 소스 URL 목록 (출처/레퍼런스로 활용)
- 시드 1개에서 여러 서브 토픽으로 확장 (e.g., 'Y2K' → 'Y2K 디님', 'Y2K 액세서리')
- 각 서브 토픽이 위 구조를 갖는 독립적인 curated_topic

### Curation scope & filtering
- 토픽 확장 수: Claude's Discretion (키워드에 따라 적절히 조절)
- 관련성 스코어링: Gemini가 토픽 생성 시 각 토픽의 관련성/트렌드성 점수를 함께 생성하도록 프롬프트
- 임계값 이하 토픽 제외
- 같은 키워드로 재실행 시 이전 결과 참조하여 중복 토픽 제외

### Error & retry behavior
- API 실패 시 재시도 전략: Claude's Discretion (exponential backoff 등)
- Grounding 결과가 빈약할 때: 그대로 저장 + low_quality 플래그 부착, 다음 단계에서 판단
- 재시도 소진 후 완전 실패 시: 에러 상태로 파이프라인 중단, 에러 상태 기록

### Claude's Discretion
- 토픽 확장 수 결정 (키워드의 범위에 따라 유동적)
- 재시도 전략 세부 설정 (횟수, 간격)
- 셀럽/브랜드 데이터와 Supabase DB 매칭 시점 (Curation vs Phase 5)
- 관련성 스코어 임계값 설정

</decisions>

<specifics>
## Specific Ideas

- Gemini + Google Search Grounding 테스트 결과, Perplexity 없이 충분한 품질 확인됨 (scripts/test_grounding.py)
- Grounding 사용 시 vogue.co.kr, harpersbazaar.co.kr, elle.co.kr 등 패션 전문 매체 소스 자동 참조
- Without Grounding은 최신 트렌드에서 할루시네이션에 가까운 결과 생성 — Grounding 필수
- 기존 `google-genai` SDK + `langchain-google-genai` 모두 프로젝트에 설치됨

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-curation-agent*
*Context gathered: 2026-02-25*
