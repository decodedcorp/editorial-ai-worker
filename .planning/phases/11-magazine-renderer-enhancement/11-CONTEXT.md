# Phase 11: Magazine Renderer Enhancement - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

기존 10개 블록 컴포넌트를 매거진 품질로 업그레이드하고, AI가 큐레이션 키워드별로 동적 디자인 스펙(폰트, 컬러, 레이아웃, 무드)을 생성하여 렌더러에 적용한다. 상세 페이지를 탭 기반으로 재구성하고, 블록별 에러 복원력을 확보한다.

**원래 Phase 11 범위 + 확장:**
- 기존: 이미지 렌더링, 타이포그래피, 에러 복원력, side-by-side 비교 뷰
- 확장: AI 동적 테마 생성 (design_spec 노드)

</domain>

<decisions>
## Implementation Decisions

### AI 동적 테마 생성
- 파이프라인에 `design_spec` 노드를 별도 추가: `curation → design_spec → editorial → enrich → review`
- Gemini가 큐레이션 키워드 + 콘텐츠 카테고리 힌트를 받아 디자인 스펙 생성
- 디자인 스펙 포함 요소: 폰트 페어링, 컬러 팔레트, 레이아웃 밀도, 무드/톤
- 저장하지 않고 매번 새로 생성 (프리뷰 시점마다 최신 트렌드 반영)

### 매거진 타이포그래피
- 혼합 폰트 전략: 헤드라인은 세리프(Georgia 계열), 본문은 산세리프(Pretendard 계열)
- AI 디자인 스펙이 구체적인 폰트 페어링을 동적으로 결정 (Google Fonts 내에서 선택)
- 기본 fallback 폰트 페어링은 Georgia + Pretendard로 고정

### 이미지 렌더링
- hero 블록 이미지 비율: AI 디자인 스펙에서 동적으로 결정 (큐레이션별 다른 비율 가능)
- 이미지 로딩 상태: 블러 플레이스홀더 → 선명하게 전환 (progressive loading)
- 이미지 로드 실패: 블러 처리 + 테마 컬러 그라데이션으로 채움 (에러 표시 없이 자연스럽게)
- product/celeb 이미지 소스: Supabase DB의 image_url 필드에서 가져옴

### Side-by-side 레이아웃 → 탭 전환
- 기존 세로 나열(Magazine Preview + Raw JSON) 구조를 탭 전환으로 변경
- [Magazine] / [JSON] 탭으로 전환, 한 번에 하나만 전체 너비로 표시
- 상세 페이지 구성: 액션바 → 메타데이터(제목, 키워드, 날짜, 리뷰 요약) → 탭 영역

### 에러 복원력
- 개별 블록의 데이터가 malformed일 때 해당 블록 위치에 인라인 경고 배너 표시
- 경고 내용: 블록 타입명 + 에러 메시지 (예: "product_showcase: Invalid data")
- 나머지 블록은 정상 렌더링 계속

### Claude's Discretion
- 에러 블록에서 원본 JSON 데이터 표시 여부 (클릭 펼치기 등)
- 디자인 스펙 Pydantic 모델의 구체적 필드 구조
- 이미지 블러 플레이스홀더 구현 방식 (CSS blur, placeholder image 등)
- 드롭캡, 행간 등 세부 타이포그래피 수치
- Google Fonts에서 선택 가능한 폰트 범위 제한

</decisions>

<specifics>
## Specific Ideas

- 디자인 스펙은 매번 새로 생성하여 항상 최신 트렌드를 반영 (캐싱 불필요)
- 폰트 기본 전략은 "프리미엄 매거진" 패턴 — 헤드라인 세리프 + 본문 산세리프
- 이미지 실패 시 "깨진 이미지" 느낌이 아닌, 자연스러운 그라데이션으로 대체
- 탭 전환은 기존 side-by-side 요구사항(SC-4)을 대체 — 동시 비교보다 전체 너비 프리뷰 우선

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-magazine-renderer-enhancement*
*Context gathered: 2026-02-26*
