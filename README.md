# Editorial AI Worker

AI 기반 K-pop/패션 매거진 에디토리얼 콘텐츠 자동 생성 파이프라인.

LangGraph 상태 기계로 트렌드 큐레이션부터 매거진 레이아웃 생성, 리뷰, 관리자 승인까지 전체 워크플로우를 자동화합니다.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Pipeline | [LangGraph](https://github.com/langchain-ai/langgraph) (StateGraph + AsyncPostgresSaver) |
| LLM | Google Gemini (2.5-flash, 2.5-pro, 2.0-flash-preview-image-generation) |
| API | FastAPI |
| Admin UI | Next.js 15 (App Router, Tailwind CSS, GSAP ScrollTrigger) |
| DB | Supabase (Postgres) — 소스 데이터 (posts, spots, solutions, celebs, products) |
| Storage | Local JSON files — 생성된 콘텐츠 (`data/contents/`) |
| Checkpointer | AsyncPostgresSaver (Supabase Postgres) — 파이프라인 상태 영속화 |
| Package | uv + hatchling, Python ≥ 3.12 |

## Pipeline Architecture

```
START → curation → design_spec → source → editorial → enrich → review → admin_gate → publish → END
                                                          ↑                  |
                                                          |    (fail, < 3회)  |
                                                          +------------------+
                                                          ↑                            |
                                                          |    (revision_requested)     |
                                                          +------- admin_gate ----------+
```

### Conditional Routing

- **review → editorial**: 리뷰 실패 시 최대 3회 재시도 (피드백 기반 수정)
- **review → admin_gate**: 리뷰 통과 시 관리자 승인 대기
- **review → END**: 3회 재시도 후에도 실패 시 파이프라인 종료
- **admin_gate → publish**: 관리자 승인 시 발행
- **admin_gate → editorial**: 관리자 수정 요청 시 피드백과 함께 재생성
- **admin_gate → END**: 관리자 거부 시 종료

## Pipeline Nodes

### 1. Curation Node

> `src/editorial_ai/nodes/curation.py` → `CurationService`

시드 키워드를 받아 트렌드를 리서치하고 구조화된 토픽을 생성합니다.

**3가지 모드:**

| Mode | 설명 | 사용 시점 |
|------|------|----------|
| `ai_curation` | Google Search Grounding으로 실시간 트렌드 리서치 → Gemini로 서브토픽 확장 → 구조화 | 기본 모드, 최신 트렌드 기반 콘텐츠 |
| `ai_db_search` | Gemini로 키워드를 DB 검색 최적화 용어로 확장 (셀럽명, 브랜드명, 한글 등) | 내부 DB 데이터 기반 콘텐츠 |
| `db_source` | 관리자가 직접 선택한 데이터 사용, 큐레이션 스킵 | 특정 포스트/셀럽/제품 지정 시 |

**핵심 로직:**
- `ai_curation`: Gemini 2.5-flash + Google Search → 트렌드 리서치 → 서브토픽 3-7개 확장 → 관련성 점수(0.6 이상) 필터링
- `ai_db_search`: Gemini로 검색어 확장 (5-10개), `_expand_keyword_for_db()` → 셀럽/브랜드 자동 추출
- 실패 시 `_fallback_topic()`으로 키워드 단순 분할 사용

**출력 상태:** `curated_topics: list[dict]` (keyword, related_keywords, celebrities, brands_products, trend_background, relevance_score)

---

### 2. Design Spec Node

> `src/editorial_ai/nodes/design_spec.py` → `DesignSpecService`

큐레이션된 키워드에 맞는 매거진 디자인 스펙을 생성합니다.

**생성 항목:**
- 폰트 페어링 (heading + body)
- 컬러 팔레트
- 레이아웃 밀도
- 무드/톤
- 히어로 이미지 종횡비
- 드롭캡 설정

**모델:** Gemini 2.5-flash-lite (response_schema=DesignSpec)

**에러 처리:** 모든 실패 시 `default_design_spec()` 반환 — 파이프라인 절대 중단하지 않음

**출력 상태:** `design_spec: dict`

---

### 3. Source Node

> `src/editorial_ai/nodes/source.py` → Supabase 직접 쿼리

큐레이션된 키워드로 Supabase DB에서 관련 포스트와 솔루션(상품) 데이터를 검색합니다.

**검색 전략:**
- `curated_topics`에서 keyword, related_keywords, celebrity names 추출
- 복합 용어를 개별 단어로 분할 (예: "Jennie Effect" → "Jennie" 추가)
- `posts` 테이블에서 `artist_name`, `group_name`, `context`, `title` ILIKE 매칭
- 검색어당 최대 5개, 전체 최대 15개 포스트
- 각 포스트에 대해 `spots → solutions` JOIN으로 관련 상품 데이터 수집

**`db_source` 모드:** `enriched_contexts`가 이미 state에 있으면 DB 쿼리 스킵

**출력 상태:** `enriched_contexts: list[dict]` (post_id, image_url, artist_name, solutions[])

---

### 4. Editorial Node

> `src/editorial_ai/nodes/editorial.py` → `EditorialService`

4단계 Gemini 파이프라인으로 매거진 레이아웃을 생성합니다.

**4-Step Pipeline:**

| Step | 모델 | 설명 |
|------|------|------|
| 1. Content Generation | Gemini 2.5-flash | 구조화된 `EditorialContent` 생성 (제목, 본문, 인용, 셀럽, 제품, 해시태그) |
| 2. Layout Image | Gemini 2.0-flash-preview-image-generation (Nano Banana) | 매거진 레이아웃 디자인 이미지 생성 |
| 3. Image Parsing | Gemini 2.5-flash-lite (Vision) | 레이아웃 이미지를 블록 시퀀스로 파싱 |
| 4. Content-Layout Merge | 로컬 로직 | EditorialContent 필드를 MagazineLayout 블록에 매핑 |

**재시도 시:**
- `feedback_history`와 `previous_draft`를 프롬프트에 포함하여 피드백 반영 수정
- 2회차 이상에서 Gemini 2.5-pro로 모델 자동 업그레이드

**이미지 저장:**
- 로컬 PNG: `data/layout_images/{thread_id}.png`
- Base64: `state["layout_image_base64"]`

**Circuit Breaker:** Nano Banana 404 시 `_image_model_available = False` → 세션 내 이미지 생성 비활성화

**출력 상태:** `current_draft: dict` (MagazineLayout), `layout_image_base64: str | None`

---

### 5. Enrich Node

> `src/editorial_ai/nodes/enrich_from_posts.py`

Editorial이 생성한 레이아웃에 실제 DB 데이터를 주입합니다.

**블록별 보강:**

| Block Type | 보강 내용 |
|-----------|----------|
| `HeroBlock` | 조회수 기준 최고 포스트 이미지 삽입 |
| `ImageGalleryBlock` | 포스트 이미지 최대 6개 채우기 |
| `CelebFeatureBlock` | 아티스트 이름 + 이미지 + 그룹 정보 |
| `ProductShowcaseBlock` | 솔루션 메타데이터 (이름, 브랜드, 썸네일, 링크) |

**출력 상태:** `current_draft: dict` (보강된 MagazineLayout)

---

### 6. Review Node

> `src/editorial_ai/nodes/review.py` → `ReviewService`

하이브리드 평가(구조적 + 의미적)로 콘텐츠 품질을 검증합니다.

**2단계 평가:**

| 단계 | 방식 | 검증 항목 |
|------|------|----------|
| Format Check | Pydantic 검증 (결정론적) | 스키마 유효성, 제목 존재, body_text 블록 존재 |
| Semantic Check | LLM-as-a-Judge (Gemini) | hallucination, fact_accuracy, content_completeness |

**적응형 루브릭:**

| ContentType | 추가 기준 |
|-------------|----------|
| FASHION_MAGAZINE | visual_appeal (0.8), trend_relevance (0.9) |
| TECH_BLOG | technical_depth, fact_accuracy (1.2) |
| LIFESTYLE | engagement |
| DEFAULT | 기본 3개 기준만 |

**타임아웃:** 60초, 초과 시 lenient pass 반환 (파이프라인 블로킹 방지)

**재시도 로직:**
- 실패 시 `revision_count` 증가 + `feedback_history` 기록 (append-only)
- 최대 3회 재시도 후 `pipeline_status = "failed"`

**출력 상태:** `review_result: dict`, `revision_count: int`, `feedback_history: list[dict]`

---

### 7. Admin Gate Node

> `src/editorial_ai/nodes/admin_gate.py` → LangGraph `interrupt()`

파이프라인을 일시정지하고 관리자 승인을 대기합니다.

**Flow:**
1. 콘텐츠를 로컬 JSON으로 저장 (`data/contents/{uuid}.json`), thread_id 기준 upsert
2. `interrupt(snapshot)` 호출 — 그래프 일시정지
3. 관리자가 Admin UI에서 결정
4. `Command(resume={"decision": "..."})` 로 재개

**관리자 결정:**

| Decision | 동작 |
|----------|------|
| `approved` | → publish 노드로 이동 |
| `revision_requested` | `admin_feedback` 저장 → editorial 노드로 재시작 |
| `rejected` | 콘텐츠 상태를 rejected로 업데이트 → END |

**출력 상태:** `admin_decision`, `admin_feedback`, `current_draft_id`

---

### 8. Publish Node

> `src/editorial_ai/nodes/publish.py` → `ContentService`

승인된 콘텐츠의 상태를 `published`로 변경합니다.

**출력 상태:** `pipeline_status: "published"`

## Pipeline State

```python
class EditorialPipelineState(TypedDict):
    # Curation
    curation_input: dict              # seed_keyword, category, mode
    curated_topics: list[dict]        # 구조화된 토픽 리스트

    # Design
    design_spec: dict | None          # 폰트, 색상, 레이아웃 스펙

    # Source
    enriched_contexts: list[dict]     # DB 포스트 + 솔루션 데이터

    # Editorial
    current_draft: dict | None        # MagazineLayout JSON
    layout_image_base64: str | None   # Nano Banana 레이아웃 이미지
    current_draft_id: str | None      # 저장된 콘텐츠 UUID

    # Review
    review_result: dict | None
    revision_count: int
    feedback_history: list[dict]      # append-only (operator.add)

    # Admin
    admin_decision: Literal["approved", "rejected", "revision_requested"] | None
    admin_feedback: str | None

    # Meta
    thread_id: str | None
    pipeline_status: Literal["curating", "sourcing", "drafting", "reviewing",
                             "awaiting_approval", "published", "failed"]
    error_log: list[str]              # append-only (operator.add)
    tool_calls_log: list[dict]        # append-only (operator.add)
```

## API Endpoints

### Pipeline

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/pipeline/trigger` | 파이프라인 실행 시작 (keyword, category, mode) |
| GET | `/api/pipeline/status/{thread_id}` | 파이프라인 상태 폴링 |
| POST | `/api/pipeline/{thread_id}/resume` | admin_gate에서 일시정지된 파이프라인 재개 |

### Contents

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/contents` | 생성된 콘텐츠 목록 (status 필터) |
| GET | `/api/contents/{id}` | 콘텐츠 상세 조회 |
| GET | `/api/contents/{id}/logs` | 파이프라인 실행 로그 (JSONL) |

### Sources

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/sources/search` | posts/celebs/products 통합 검색 |
| POST | `/api/sources/resolve` | 선택된 소스 ID로 파이프라인 입력 데이터 구성 |

## Admin UI

Next.js 15 기반 관리자 대시보드. BFF(Backend for Frontend) 패턴으로 Python API를 프록시합니다.

### 주요 기능
- **콘텐츠 목록**: 상태별 필터, 파이프라인 요약 (비용, 소요시간, 재시도 횟수)
- **콘텐츠 상세**: Magazine 프리뷰 | Layout Image | JSON | Pipeline 로그 탭
- **새 콘텐츠 생성**: AI Curation / AI DB Search / DB Source 3가지 모드
- **매거진 프리뷰**: GSAP ScrollTrigger 애니메이션, 54개 레이아웃 변형 (10 블록 타입)

### GSAP Animation System

모든 블록은 `BlockRenderer` → `AnimatedBlock`으로 래핑되어 스크롤 기반 GSAP 애니메이션이 적용됩니다.

**동작 방식:**
- `gsap.registerPlugin(ScrollTrigger)` 로 스크롤 트리거 등록
- 각 블록의 `animation` 필드 값에 따라 진입 애니메이션 적용
- **Above-fold 최적화**: 처음 2개 블록 (hero + headline)은 애니메이션 스킵 → 즉시 표시
- 블록 인덱스에 따라 `delay` 스태거링: `(index - 2) * 0.05s`

**Animation Presets (AI가 블록별 선택):**

| Name | 효과 | GSAP Vars |
|------|------|-----------|
| `fade-up` | 아래에서 위로 페이드인 (기본값) | `y: 40 → 0, opacity: 0 → 1` |
| `fade-in` | 제자리 페이드인 | `opacity: 0 → 1` |
| `slide-left` | 왼쪽에서 슬라이드 | `x: -60 → 0` |
| `slide-right` | 오른쪽에서 슬라이드 | `x: 60 → 0` |
| `scale-in` | 축소에서 확대 | `scale: 0.9 → 1` |
| `parallax` | 깊은 페이드업 (느린 속도) | `y: 60 → 0, duration: 1.2s` |
| `none` | 애니메이션 없음 | — |

**ScrollTrigger 설정:**
- `start: "top 90%"` — 블록이 뷰포트 90% 지점에 도달하면 트리거
- `toggleActions: "play none none none"` — 한 번만 재생
- `ease: "power2.out"`, 기본 `duration: 0.7s`

### Layout Variant Width System

`layout_variant` 값에 따라 블록의 컨테이너 너비가 자동 결정됩니다:

| Width Class | Variants | 적용 |
|-------------|----------|------|
| `w-full` (full bleed) | `full_bleed`, `parallax`, `letterbox`, `split_text_*`, `full_bleed_grid`, `full_bleed_single`, `staggered_overlap`, `full_width_*`, `lookbook`, `hero_collage`, `color_band`, `gradient_fade`, `floating` | 화면 전체 너비 |
| `max-w-5xl` (wide) | `wide`, `featured_plus_grid`, `carousel_cards`, `card_row`, `filmstrip`, `centered_large`, `oversized_serif`, `spotlight` | 넓은 컨테이너 |
| `max-w-xl` (narrow) | `narrow_centered` | 좁은 중앙 정렬 |
| `max-w-3xl` (default) | 기타 모든 variant | 기본 컨테이너 |

### DesignSpec Integration

`DesignSpecProvider` (React Context)를 통해 AI가 생성한 디자인 스펙이 모든 블록에 전달됩니다:

```
MagazinePreview → DesignSpecProvider → BlockRenderer → 각 Block Component
```

**적용 항목:**
- `color_palette.primary/accent/background`: 배경색, 드롭캡 색상, 구분선 색상, 그라데이션
- `font_pairing`: Playfair Display (heading), Noto Sans KR (body)
- `hero_aspect_ratio`: 히어로 이미지 종횡비 (기본 16/9)
- `drop_cap`: 첫 문단 드롭캡 표시 여부
- `layout_density`: compact / normal / spacious

### Block Types — 54 Layout Variants

#### `hero` — 히어로 이미지 (6 variants)

| Variant | 설명 | 특징 |
|---------|------|------|
| `contained` | 라운드 코너 컨테이너 (기본) | aspect-ratio from DesignSpec, 하단 그라데이션 오버레이 |
| `full_bleed` | 전체 화면 (90vh) | edge-to-edge, 강한 그라데이션 `from-black/70` |
| `split_text_left` | 좌측 텍스트 + 우측 이미지 | 2컬럼 그리드, primary 색상 텍스트 패널 |
| `split_text_right` | 좌측 이미지 + 우측 텍스트 | split_text_left 미러 |
| `parallax` | 패럴랙스 배경 (85vh) | `will-change-transform`, 이미지 120% 크기로 오버플로 |
| `letterbox` | 시네마틱 21:9 크롭 | `aspect-[21/9]`, uppercase tracking-wider 텍스트 |

#### `headline` — 섹션 제목 (4 variants)

| Variant | 설명 | 특징 |
|---------|------|------|
| `default` | 표준 제목 + 액센트 언더라인 | h1/h2/h3 레벨별 크기, accent 색상 3px bar |
| `full_width_banner` | 전체 너비 배너 | primary 배경색, 흰색 텍스트, 중앙 정렬 |
| `left_aligned_large` | 초대형 좌측 정렬 | `text-6xl md:text-8xl`, tracking-tighter |
| `overlapping` | 고스트 텍스트 + 실제 텍스트 | 배경에 `opacity-[0.07]` 초대형 텍스트 중첩 |

#### `body_text` — 본문 텍스트 (6 variants)

| Variant | 설명 | 특징 |
|---------|------|------|
| `single_column` | 단일 컬럼 (기본) | 17px, line-height 1.8, DesignSpec 드롭캡 |
| `two_column` | 2단 컬럼 | CSS `columns-2`, `break-inside-avoid` |
| `three_column` | 3단 컬럼 | 반응형 `columns-1 md:columns-2 lg:columns-3` |
| `wide` | 넓은 텍스트 | `text-lg`, line-height 2.0 |
| `narrow_centered` | 좁은 중앙 정렬 | 중앙 정렬 + line-height 2.0 |
| `drop_cap_accent` | 강조 드롭캡 | 5rem 드롭캡 + accent 색상 좌측 border |

#### `image_gallery` — 이미지 갤러리 (8 variants)

| Variant | 설명 | 특징 |
|---------|------|------|
| `grid` | 2열 그리드 (기본) | 정사각 1:1, 캡션 표시 |
| `carousel` | 가로 스크롤 | `w-64` 고정 너비, `overflow-x-auto` |
| `masonry` | 벽돌형 | CSS `columns-2`, 3:4 비율 |
| `full_bleed_grid` | 밀착 그리드 | 2-4열, `gap-1`, 라운드 없음, 캡션 없음 |
| `asymmetric` | 비대칭 | 첫 이미지 full-width 16:10, 나머지 2열 그리드 |
| `full_bleed_single` | 풀 너비 스택 | 각 이미지 16:9, 라운드 없음 |
| `staggered_overlap` | 콜라주 겹침 | 교차 너비 + 네거티브 마진으로 겹침 효과 |
| `filmstrip` | 필름스트립 | 가로 스크롤 21:9, 흰색 보더 |

#### `pull_quote` — 인용구 (5 variants)

| Variant | 설명 | 특징 |
|---------|------|------|
| `default` | 좌측 accent 보더 | 3px border-left, Georgia serif |
| `centered_large` | 대형 중앙 정렬 | 6xl 인용부호, `text-3xl md:text-4xl` |
| `full_width_background` | 전체 너비 배경 | accent 색상 15% 투명도 배경 |
| `sidebar` | 사이드바 플로팅 | `float-right w-64`, 본문 옆 배치 |
| `oversized_serif` | 초대형 serif | `text-5xl md:text-6xl`, tracking `0.2em` 출처 |

#### `celeb_feature` — 셀럽 프로필 (5 variants)

| Variant | 설명 | 특징 |
|---------|------|------|
| `grid` | 원형 프로필 그리드 (기본) | `size-28` 원형, 2-3열 |
| `spotlight` | 첫 셀럽 스포트라이트 | 2컬럼 (이미지 3:4 + 텍스트), 나머지 `size-16` 원형 |
| `card_row` | 카드형 가로 스크롤 | `w-56`, 2:3 비율, 하단 그라데이션 오버레이 |
| `minimal_list` | 미니멀 리스트 | `size-10` 원형 + 텍스트, 구분선 |
| `hero_collage` | 콜라주 겹침 | 최대 5명, 절대 위치로 겹치는 레이아웃 |

#### `product_showcase` — 제품 쇼케이스 (6 variants)

| Variant | 설명 | 특징 |
|---------|------|------|
| `grid` | 카드 그리드 (기본) | 2-3열, hover 확대 효과, 링크 연동 |
| `full_width_row` | 가로 스크롤 행 | `w-48` 고정, `overflow-x-auto` |
| `featured_plus_grid` | 피처드 + 그리드 | 첫 제품 16:10 대형, 나머지 그리드 |
| `minimal_list` | 미니멀 리스트 | 이미지 없음, 이름/브랜드 + 설명 |
| `lookbook` | 룩북 | 교차 이미지-텍스트 레이아웃 (3:2 컬럼) |
| `carousel_cards` | 캐러셀 카드 | `snap-x snap-mandatory`, 3:4 비율, hover shadow |

#### `divider` — 구분선 (6 variants)

| Variant | 설명 |
|---------|------|
| `line` | 기본 수평선 (`border-gray-200`) |
| `space` | 여백만 (`h-12`) |
| `ornament` | 장식 점 3개 (`· · ·`) |
| `full_bleed_line` | 전체 너비 선 (`border-gray-300`) |
| `color_band` | accent 색상 밴드 (`h-2`) |
| `gradient_fade` | 그라데이션 페이드 (`h-16`, transparent → gray → transparent) |

#### `hashtag_bar` — 해시태그 (4 variants)

| Variant | 설명 |
|---------|------|
| `default` | pill 형태 태그 (rounded-full, border, hover 효과) |
| `full_width_banner` | 전체 너비 배너 (accent 15% 배경) |
| `minimal_inline` | 슬래시 구분 인라인 텍스트 |
| `floating` | 크기/투명도 변형 (font-size + opacity 순환) |

#### `credits` — 크레딧 (4 variants)

| Variant | 설명 |
|---------|------|
| `default` | 상단 border + 2열 그리드 (role/name) |
| `full_width_footer` | 다크 풀 너비 푸터 (`bg-gray-900`, 3열) |
| `inline` | 한 줄 인라인 (슬래시 구분) |
| `sidebar_column` | 우측 정렬 사이드바 (`max-w-[200px]`) |

## Project Structure

```
editorial-ai-worker/
├── src/editorial_ai/
│   ├── graph.py               # LangGraph StateGraph 토폴로지
│   ├── state.py               # 파이프라인 공유 상태
│   ├── config.py              # Pydantic Settings (환경변수)
│   ├── checkpointer.py        # AsyncPostgresSaver
│   ├── nodes/                 # 파이프라인 노드 구현
│   │   ├── curation.py        # 트렌드 큐레이션
│   │   ├── design_spec.py     # 디자인 스펙 생성
│   │   ├── source.py          # Supabase DB 검색
│   │   ├── editorial.py       # 4단계 콘텐츠 생성
│   │   ├── enrich_from_posts.py  # 실제 데이터 보강
│   │   ├── review.py          # 하이브리드 품질 평가
│   │   ├── admin_gate.py      # 관리자 승인 게이트
│   │   ├── publish.py         # 발행
│   │   └── stubs.py           # 테스트용 스텁
│   ├── services/              # 비즈니스 로직
│   │   ├── curation_service.py
│   │   ├── design_spec_service.py
│   │   ├── editorial_service.py
│   │   ├── review_service.py
│   │   ├── content_service.py
│   │   ├── enrich_service.py  # (legacy)
│   │   └── supabase_client.py
│   ├── models/                # Pydantic 데이터 모델
│   │   ├── layout.py          # MagazineLayout, Block types
│   │   ├── editorial.py       # EditorialContent
│   │   ├── curation.py        # CuratedTopic, CurationResult
│   │   ├── design_spec.py     # DesignSpec
│   │   ├── review.py          # ReviewResult
│   │   ├── celeb.py
│   │   ├── post.py
│   │   └── product.py
│   ├── api/                   # FastAPI 앱
│   │   ├── app.py
│   │   ├── schemas.py
│   │   └── routes/
│   ├── prompts/               # LLM 프롬프트 빌더
│   ├── routing/               # YAML 기반 모델 라우터
│   ├── rubrics/               # 콘텐츠 타입별 리뷰 루브릭
│   ├── observability/         # 노드 타이밍/토큰 로깅
│   └── caching/               # Gemini 캐싱
├── admin/                     # Next.js 15 Admin UI
│   └── src/
│       ├── app/
│       │   ├── api/           # BFF 프록시 라우트
│       │   └── contents/      # 콘텐츠 상세 페이지
│       ├── components/        # React 컴포넌트
│       └── lib/               # 타입, 유틸리티
├── data/
│   ├── contents/              # 생성된 콘텐츠 JSON
│   ├── layout_images/         # 레이아웃 이미지 PNG
│   └── logs/                  # 파이프라인 JSONL 로그
├── supabase/                  # 마이그레이션
├── tests/                     # pytest
└── pyproject.toml
```

## Setup

```bash
# Python 환경
uv sync

# 환경변수 설정
cp .env.example .env
# GOOGLE_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, DATABASE_URL 등 설정

# API 서버 실행
uv run uvicorn editorial_ai.api.app:app --reload --port 8000

# Admin UI 실행
cd admin && npm install && npm run dev

# 테스트
uv run pytest
```

## Key Design Decisions

1. **Lean State Principle**: 파이프라인 상태에는 ID와 참조만 저장. 무거운 페이로드는 외부(Supabase, 로컬 JSON)에 보관.
2. **Human-in-the-Loop**: LangGraph `interrupt()`로 admin_gate에서 그래프 일시정지. `Command(resume=...)` 로 정확히 중단 지점에서 재개.
3. **Observability as Decorator**: 모든 노드가 `node_wrapper()`로 래핑되어 타이밍, 토큰 사용량, 상태 스냅샷을 JSONL 로그로 자동 기록.
4. **Model Routing**: YAML 설정 기반 노드별 Gemini 모델 매핑. 재시도 2회 이상 시 자동 업그레이드 (flash → pro).
5. **Local-First Content Storage**: 생성된 콘텐츠는 `data/contents/`에 로컬 JSON으로 저장. Supabase는 소스 데이터 읽기 전용.
6. **Circuit Breaker**: Nano Banana 이미지 생성 404 시 자동 비활성화, fallback 템플릿 사용.
