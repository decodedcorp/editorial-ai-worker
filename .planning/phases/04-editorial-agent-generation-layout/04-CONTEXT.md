# Phase 4: Editorial Agent - Generation + Layout - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

큐레이션된 키워드와 트렌드 자료를 입력받아 에디토리얼 콘텐츠를 생성하고, 나노바나나 AI로 매거진 레이아웃 디자인을 생성한 뒤, 이를 Magazine Layout JSON으로 구조화하여 출력한다. 프론트엔드 렌더러는 별도 구현이며, 이 Phase에서 만드는 JSON 스키마가 렌더러의 설계 스펙 역할을 한다.

</domain>

<decisions>
## Implementation Decisions

### Layout JSON 출력 형태
- 최종 출력은 JSON → 프론트엔드(decoded-editorial)가 렌더링
- 프론트엔드 렌더러는 아직 없음, JSON 스키마가 렌더러 스펙 역할
- 이 프로젝트에서 스키마를 정의하고 프론트엔드가 따르는 구조
- schema_version 필드 포함하여 스키마 버전닝 지원

### 섹션 타입 설계
- 어떤 블록 타입들이 필요한지는 리서처가 패션 매거진 레이아웃 패턴을 조사하여 결정
- 블록 기반 스키마 vs 자유 레이아웃 접근 방식도 리서치 필요

### 나노바나나 AI 통합
- 매 에디토리얼마다 키워드별 레이아웃 디자인을 나노바나나로 동적 생성
- 파이프라인 위치: 콘텐츠 생성 후 호출 (콘텐츠 + 키워드 → 나노바나나 → 레이아웃)
- 나노바나나 디자인 이미지 → JSON 구조 변환 방법은 리서치 필요 (Vision AI 파싱, API 구조화 출력 등)
- 변환 신뢰성 전략도 리서치에서 조사
- Fallback: 재시도 후 실패 시 기본 템플릿 사용
- 레이아웃 다양성: 하이브리드 (기본 템플릿 + 나노바나나 커스터마이즈)

### 이미지 소싱
- DB(Supabase)에 저장된 셀럽/상품 이미지만 사용
- AI 이미지 생성 없음 — 실제 상품/셀럽 사진 우선

### 에디토리얼 톤/스타일
- decoded 기존 톤을 따르되, 참고 소스가 없어 실제 생성 결과를 보면서 반복 조정 필요
- 일단 짧은 형식(500자 내외)으로 시작
- 언어: 한국어 우선, 다국어 확장은 나중 Phase에서

### 콘텐츠 구성
- 1 키워드 = 1 에디토리얼
- 입력: 키워드 + curation 트렌드 자료 + 관련 서치 결과를 컨텍스트로 활용
- 셀럽/상품은 placeholder로 자리만 마련 (Phase 5에서 DB Tool로 채움)
- 셀럽/상품 수량: 키워드에 따라 유동적
- 추가 콘텐츠 요소(인용문, 해시태그 등): Claude 재량

### 파이프라인 흐름
1. 키워드 + curation 컨텍스트 입력
2. LLM이 에디토리얼 콘텐츠 생성 (텍스트, 요소)
3. 콘텐츠 + 키워드 → 나노바나나 레이아웃 디자인 생성
4. 디자인 이미지 → JSON 구조 파싱
5. 콘텐츠를 JSON 구조에 배치
6. 최종 Layout JSON 출력

### 생성 실패 복구
- Gemini structured output 실패 시 복구 전략: Claude 재량
- 나노바나나 실패 시: 재시도 후 기본 템플릿 fallback
- 전체 파이프라인 실패 시: Claude 재량

### Claude's Discretion
- 섹션 타입 목록 (리서치 결과 기반으로 결정)
- 블록 기반 vs 자유 레이아웃 스키마 설계 방식
- 추가 콘텐츠 요소 (인용문, 해시태그 등)
- Gemini structured output 복구 전략
- 전체 파이프라인 실패 처리

</decisions>

<specifics>
## Specific Ideas

- 나노바나나 AI를 활용해 매번 키워드에 맞는 고유한 매거진 레이아웃 디자인을 동적 생성하는 것이 핵심 차별점
- 레이아웃 퀄리티가 전체 콘텐츠 퀄리티를 좌우 — 단순 카드 나열이 아닌 진짜 매거진처럼 보여야 함
- 톤/스타일은 한 번에 정하기 어렵고, 생성 결과를 반복적으로 확인하면서 조정하는 과정이 필요
- 레퍼런스가 없으므로 리서처가 패션 에디토리얼 레이아웃 패턴을 적극 조사해야 함

</specifics>

<deferred>
## Deferred Ideas

- 다국어 지원 — 한국어 우선, 확장은 별도 Phase에서
- AI 이미지 생성 (배경, 분위기 사진 등) — 현재는 DB 이미지만 사용

</deferred>

---

*Phase: 04-editorial-agent-generation-layout*
*Context gathered: 2026-02-25*
