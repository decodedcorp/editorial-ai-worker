# Phase 5: Editorial Agent - DB Tools - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Editorial Agent가 Supabase에서 관련 셀럽/인플루언서와 상품/브랜드를 검색하여 초안에 반영하는 상태. Phase 4에서 생성된 에디토리얼 초안을 DB 데이터로 enrichment하여 실제 셀럽/상품 정보가 포함된 최종 초안을 만든다.

</domain>

<decisions>
## Implementation Decisions

### 검색 매칭 전략
- LLM 연관 키워드 확장 후 DB 검색: Gemini로 키워드에서 연관 검색어 생성(e.g. 'Y2K'→'레트로,빈티지') 후 Supabase 검색
- 병행 검색: EditorialContent의 celeb_mentions/product_mentions 이름 + 키워드 확장 결과 모두로 검색, 중복 제거 후 합산

### 초안 반영 방식
- 콘텐츠 재생성: DB에서 가져온 셀럽/상품 정보를 컨텍스트로 주고 Gemini로 콘텐츠 전체를 재생성
- 본문 통합: 셀럽/상품 정보가 BodyTextBlock 본문에도 자연스럽게 언급되도록 재생성
- CelebFeatureBlock/ProductShowcaseBlock에 실제 DB ID와 상세정보 포함

### 노드 아키텍처
- 별도 enrich_editorial 노드를 editorial 뒤에 추가 (editorial → enrich → review)
- editorial_node는 Phase 4 그대로 유지, enrich 노드가 DB 검색 + 콘텐츠 재생성 담당

### Claude's Discretion
- 셀럽/상품 수량 (콘텐츠 성격에 따라 유동적으로 결정)
- 검색 결과 정렬/우선순위 기준 (DB 스키마와 가용 데이터에 따라)
- DB 매칭 실패 시 빈 결과 처리 방식
- Tool binding vs 직접 서비스 호출 (연구 후 결정)
- 프론트엔드 연동 방식 (ID만 vs 전체 정보 임베딩)

</decisions>

<specifics>
## Specific Ideas

- DB 검색은 멘션 이름 매칭과 키워드 확장 결과를 병행하여 폭넓은 매칭 보장
- enrichment 후 콘텐츠가 자연스럽게 읽히는 것이 중요 — 단순 데이터 삽입이 아니라 재생성

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-editorial-agent-db-tools*
*Context gathered: 2026-02-25*
