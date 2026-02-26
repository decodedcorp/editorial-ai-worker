# Editorial AI Worker — System Specification

> 패션 매거진 콘텐츠를 자동 생성하는 멀티 에이전트 파이프라인
> LangGraph + Google Gemini + Supabase 기반

---

## 1. 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI (REST API)                      │
│  /api/pipeline/trigger  /api/contents/*  /api/contents/logs  │
└────────────────────────────┬────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  LangGraph Core  │
                    │  (StateGraph)    │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
   ┌─────▼─────┐   ┌────────▼────────┐   ┌──────▼──────┐
   │  Gemini    │   │  Supabase       │   │  Postgres   │
   │  (LLM)    │   │  (Data Source)  │   │  (Checkpoint)│
   └───────────┘   └─────────────────┘   └─────────────┘
```

**핵심 기술 스택:**
| 기술 | 역할 |
|------|------|
| LangGraph ≥1.0.9 | 멀티 노드 상태 그래프 오케스트레이션 |
| Google Gemini (google-genai) | 콘텐츠 생성, 리뷰, 큐레이션 |
| Supabase (AsyncClient) | 포스트/솔루션 데이터 소싱, 콘텐츠 저장 |
| PostgreSQL (AsyncPostgresSaver) | LangGraph 상태 체크포인팅 |
| FastAPI | REST Admin API |
| Pydantic v2 | 스키마 검증 & Structured Output |

---

## 2. 파이프라인 토폴로지

```
START
  │
  ▼
┌──────────┐    ┌─────────────┐    ┌────────┐    ┌───────────┐
│ curation │───▶│ design_spec │───▶│ source │───▶│ editorial │
└──────────┘    └─────────────┘    └────────┘    └─────┬─────┘
                                                       │
                                                       ▼
                                                 ┌──────────┐
                                          ┌─────▶│  enrich  │
                                          │      └────┬─────┘
                                          │           │
                                          │           ▼
                                   retry  │     ┌──────────┐
                              (max 3회)   │     │  review  │
                                          │     └────┬─────┘
                                          │          │
                                     ┌────┘    pass? │
                                     │          ├────┴────┐
                                     │          │ fail    │ pass
                                     │          ▼         ▼
                                     │    editorial  ┌───────────┐
                                     │               │admin_gate │
                                     │               └─────┬─────┘
                                     │                     │
                                     │          ┌──────────┼──────────┐
                                     │          │          │          │
                                     │     approved   revision   rejected
                                     │          │     requested     │
                                     │          ▼          │        ▼
                                     │    ┌─────────┐     │      END
                                     │    │ publish │     │
                                     │    └─────────┘     │
                                     │          │         │
                                     │          ▼         │
                                     │        END ◀───────┘
                                     │               (→ editorial retry)
                                     └────────────────────┘
```

**라우팅 규칙:**
- **review → admin_gate**: `review_result.passed == True`
- **review → editorial (retry)**: `review_result.passed == False AND revision_count < 3`
- **review → END**: `review_result.passed == False AND revision_count ≥ 3` (에스컬레이션)
- **admin_gate → publish**: `admin_decision == "approved"`
- **admin_gate → editorial**: `admin_decision == "revision_requested"`
- **admin_gate → END**: `admin_decision == "rejected"`

---

## 3. 파이프라인 노드 상세

### 3.1 Curation Node

| 항목 | 값 |
|------|-----|
| 파일 | `src/editorial_ai/nodes/curation.py` |
| 서비스 | `CurationService` |
| 모델 | gemini-2.5-flash |
| 입력 | `curation_input.seed_keyword` |
| 출력 | `curated_topics: list[CuratedTopic]` |

**동작:**
1. Gemini + **Google Search Grounding** → 실시간 트렌드 리서치
2. Gemini Structured Output → `CuratedTopic[]` JSON 추출
3. 관련 서브토픽 확장 (2-3개)
4. `relevance_score` 기반 품질 필터링 (`low_quality=True` 제거)

**CuratedTopic 스키마:**
```python
class CuratedTopic(BaseModel):
    keyword: str
    trend_background: str
    related_keywords: list[str]
    celebrities: list[CelebRef]      # name, relevance
    brands_products: list[BrandRef]  # name, relevance
    seasonality: str | None
    sources: list[str]               # Google Search URL
    relevance_score: float           # 0.0 ~ 1.0
    low_quality: bool
```

---

### 3.2 Design Spec Node

| 항목 | 값 |
|------|-----|
| 파일 | `src/editorial_ai/nodes/design_spec.py` |
| 서비스 | `DesignSpecService` |
| 모델 | gemini-2.5-flash |
| 입력 | `curated_topics[0].keyword` |
| 출력 | `design_spec: DesignSpec` |

**DesignSpec 스키마:**
```python
class DesignSpec(BaseModel):
    color_palette: dict   # primary, secondary, accent
    typography: dict      # font_family, sizes
    layout_grid: dict     # column_count, gutter_width
    visual_style: str     # modern / classic / playful
```

**폴백:** 에러 발생 시 기본 템플릿 반환

---

### 3.3 Source Node

| 항목 | 값 |
|------|-----|
| 파일 | `src/editorial_ai/nodes/source.py` |
| 서비스 | Supabase Direct Query |
| 모델 | 없음 (DB 쿼리만) |
| 입력 | `curated_topics` (키워드 + 셀럽명) |
| 출력 | `enriched_contexts: list[dict]` |

**동작:**
1. `curated_topics`에서 검색어 추출 (키워드, related_keywords, 셀럽명)
2. 복합어 분리 확장 (예: "Jennie Effect" → "Jennie", "Effect")
3. Supabase `posts` 테이블 쿼리:
   - `artist_name.ilike`, `group_name.ilike`, `context.ilike`, `title.ilike`
   - `status = "active"`, `view_count DESC`
   - 검색어당 최대 5개, 총 최대 15개
4. 각 포스트의 `spots → solutions` (상품) 조인

**출력 구조:**
```json
{
  "post_id": "...",
  "image_url": "https://...",
  "artist_name": "Jennie",
  "group_name": "BLACKPINK",
  "context": "공항패션",
  "view_count": 12345,
  "solutions": [
    {
      "solution_id": "...",
      "title": "Chanel Classic Flap",
      "thumbnail_url": "https://...",
      "metadata": {"keywords": [...], "qa_pairs": [...]},
      "link_type": "affiliate"
    }
  ]
}
```

---

### 3.4 Editorial Node

| 항목 | 값 |
|------|-----|
| 파일 | `src/editorial_ai/nodes/editorial.py` |
| 서비스 | `EditorialService` |
| 모델 | gemini-2.5-flash (기본), gemini-2.5-pro (리비전 ≥2) |
| 입력 | `curated_topics`, `enriched_contexts`, `feedback_history` |
| 출력 | `current_draft: MagazineLayout` |

**4단계 생성 파이프라인:**

| 단계 | 설명 | 모델 |
|------|------|------|
| 1. Content Gen | Gemini Structured Output → `EditorialContent` | gemini-2.5-flash/pro |
| 2. Layout Image | Nano Banana 이미지 생성 → 레이아웃 디자인 이미지 | gemini-2.0-flash-preview-image-generation |
| 3. Layout Parse | Gemini Vision → 이미지에서 블록 구조 JSON 추출 | gemini-2.5-flash |
| 4. Merge | 콘텐츠를 레이아웃 블록에 매핑 | 로직만 |

**EditorialContent 스키마:**
```python
class EditorialContent(BaseModel):
    keyword: str
    title: str
    subtitle: str
    body_paragraphs: list[str]
    pull_quotes: list[str]
    product_mentions: list[ProductMention]  # name, brand, context
    celeb_mentions: list[CelebMention]      # name, context
    hashtags: list[str]
    credits: list[CreditEntry]              # role, name
```

**모델 라우팅:**
- `revision_count < 2` → gemini-2.5-flash
- `revision_count ≥ 2` → gemini-2.5-pro (자동 업그레이드)

**출력 복구 루프:** JSON 파싱 실패 시 → 마크다운 펜스 제거 → Gemini repair (최대 2회)

---

### 3.5 Enrich Node

| 항목 | 값 |
|------|-----|
| 파일 | `src/editorial_ai/nodes/enrich_from_posts.py` |
| 서비스 | 없음 (순수 매핑 로직) |
| 입력 | `current_draft`, `enriched_contexts` |
| 출력 | `current_draft` (실제 데이터 주입) |

**블록별 실데이터 주입:**

| 블록 타입 | 주입 데이터 |
|-----------|------------|
| HeroBlock | 최고 view_count 포스트 이미지 |
| ImageGalleryBlock | 포스트 이미지 1~6 |
| CelebFeatureBlock | 유니크 아티스트 목록 |
| ProductShowcaseBlock | 솔루션(상품) 목록 |

---

### 3.6 Review Node

| 항목 | 값 |
|------|-----|
| 파일 | `src/editorial_ai/nodes/review.py` |
| 서비스 | `ReviewService` |
| 모델 | gemini-2.5-flash (기본), gemini-2.5-pro (리비전 ≥2) |
| 입력 | `current_draft`, `curated_topics` |
| 출력 | `review_result: ReviewResult` |

**하이브리드 평가 (Format + Semantic):**

| 단계 | 방식 | 검증 내용 |
|------|------|----------|
| 1. Format Validation | Pydantic (결정적) | 스키마 검증, 비어있지 않은 제목, body_text 블록 존재 |
| 2. Semantic Evaluation | LLM-as-a-Judge (Gemini, temp=0.0) | hallucination, fact_accuracy, content_completeness |

**적응형 루브릭 시스템:**

| 콘텐츠 타입 | 평가 기준 |
|------------|----------|
| fashion_magazine | hallucination(1.0), fact_accuracy(1.0), content_completeness(1.0), visual_appeal(0.8), trend_relevance(0.9) |
| tech_blog | hallucination, technical_accuracy, content_depth |
| lifestyle | hallucination, authenticity, engagement |
| default | hallucination, fact_accuracy, content_completeness |

**ReviewResult 스키마:**
```python
class ReviewResult(BaseModel):
    passed: bool                          # 모든 기준 통과 여부
    criteria: list[CriterionResult]       # 기준별 결과
    summary: str                          # 평가 요약
    suggestions: list[str]                # 개선 제안

class CriterionResult(BaseModel):
    criterion: str
    passed: bool
    reason: str
    severity: Literal["critical", "major", "minor"]
```

---

### 3.7 Admin Gate Node

| 항목 | 값 |
|------|-----|
| 파일 | `src/editorial_ai/nodes/admin_gate.py` |
| 동작 | LangGraph `interrupt()` — Human-in-the-Loop |
| 입력 | `current_draft`, `thread_id` |
| 출력 | `admin_decision`, `current_draft_id` |

**동작:**
1. `current_draft`를 Supabase `editorial_contents`에 pending으로 저장 (thread_id 기준 upsert)
2. `interrupt()` 호출 → 그래프 일시정지
3. Admin이 API로 승인/거절/수정요청
4. 그래프 재개 후 `admin_decision`에 따라 라우팅

---

### 3.8 Publish Node

| 항목 | 값 |
|------|-----|
| 파일 | `src/editorial_ai/nodes/publish.py` |
| 동작 | Supabase 상태 업데이트 |
| 입력 | `current_draft_id` |
| 출력 | `pipeline_status = "published"` |

---

## 4. 파이프라인 상태 스키마

`EditorialPipelineState` (TypedDict):

| 필드 | 타입 | 설명 |
|------|------|------|
| `curation_input` | dict | 사용자 입력 (seed_keyword, category, tone, style, target_celeb, target_brand) |
| `curated_topics` | list[dict] | 큐레이션 결과 |
| `design_spec` | dict \| None | 디자인 스펙 |
| `enriched_contexts` | list[dict] | Supabase 포스트/솔루션 데이터 |
| `current_draft` | dict \| None | MagazineLayout JSON |
| `current_draft_id` | str \| None | Supabase content ID |
| `tool_calls_log` | list[dict] | 도구 호출 로그 (누적) |
| `review_result` | dict \| None | 리뷰 결과 |
| `revision_count` | int | 리비전 횟수 (최대 3) |
| `feedback_history` | list[dict] | 리뷰 피드백 이력 (누적) |
| `thread_id` | str \| None | 파이프라인 실행 ID |
| `admin_decision` | Literal | "approved" \| "rejected" \| "revision_requested" |
| `admin_feedback` | str \| None | 관리자 피드백 |
| `pipeline_status` | Literal | "curating" \| "sourcing" \| "drafting" \| "reviewing" \| "awaiting_approval" \| "published" \| "failed" |
| `error_log` | list[str] | 에러 로그 (누적) |

---

## 5. 데이터 모델 — MagazineLayout

**핵심 출력 데이터 모델** (`src/editorial_ai/models/layout.py`)

```
MagazineLayout
├── keyword: str
├── title: str
├── blocks: list[Block]          ← 블록 리스트 (discriminated union)
├── metadata: list[KeyValuePair]
└── design_spec: DesignSpec
```

**블록 타입:**

| 블록 | 설명 | 주요 필드 |
|------|------|----------|
| HeroBlock | 히어로 이미지 + 오버레이 텍스트 | image_url, overlay_title, overlay_subtitle |
| HeadlineBlock | 제목 텍스트 | text, level (1~3) |
| BodyTextBlock | 본문 단락 | paragraphs[] |
| ImageGalleryBlock | 이미지 갤러리 | images[], layout_style (grid/carousel/masonry) |
| PullQuoteBlock | 인용문 | quote |
| ProductShowcaseBlock | 상품 쇼케이스 | products[] (product_id, name, brand, image_url, description) |
| CelebFeatureBlock | 셀럽 피처 | celebs[] (celeb_id, name, image_url, description) |
| DividerBlock | 구분선 | — |
| HashtagBarBlock | 해시태그 바 | hashtags[] |
| CreditsBlock | 크레딧 | entries[] (role, name) |

---

## 6. API 엔드포인트

### 6.1 파이프라인 관리

| Method | Endpoint | Auth | 설명 |
|--------|----------|------|------|
| POST | `/api/pipeline/trigger` | X-API-Key | 파이프라인 실행 시작 |
| GET | `/api/pipeline/status/{thread_id}` | X-API-Key | 실행 상태 폴링 |

**Trigger Request:**
```json
{
  "seed_keyword": "Jennie Effect",
  "category": "fashion",
  "tone": "sophisticated",
  "style": "editorial",
  "target_celeb": "Jennie",
  "target_brand": null
}
```

**Status Response:**
```json
{
  "thread_id": "uuid",
  "pipeline_status": "reviewing",
  "error_log": [],
  "has_draft": true
}
```

### 6.2 콘텐츠 관리 (Admin)

| Method | Endpoint | Auth | 설명 |
|--------|----------|------|------|
| GET | `/api/contents/` | X-API-Key | 콘텐츠 목록 (페이지네이션, status 필터) |
| GET | `/api/contents/{id}` | X-API-Key | 콘텐츠 상세 |
| POST | `/api/contents/{id}/approve` | X-API-Key | 콘텐츠 승인 → 그래프 재개 |
| POST | `/api/contents/{id}/reject` | X-API-Key | 콘텐츠 거절 → 그래프 재개 |

### 6.3 옵저버빌리티

| Method | Endpoint | Auth | 설명 |
|--------|----------|------|------|
| GET | `/api/contents/{id}/logs` | X-API-Key | 노드별 실행 로그 + 토큰 사용량 |

**Logs Response:**
```json
{
  "content_id": "uuid",
  "runs": [
    {
      "node_name": "curation",
      "status": "success",
      "duration_ms": 1234.5,
      "token_usage": [{"prompt_tokens": 100, "completion_tokens": 50, "model_name": "gemini-2.5-flash"}],
      "total_tokens": 150
    }
  ],
  "summary": {
    "node_count": 8,
    "total_duration_ms": 45000,
    "total_tokens": 1500,
    "status": "published"
  }
}
```

### 6.4 헬스체크

| Method | Endpoint | Auth | 설명 |
|--------|----------|------|------|
| GET | `/health` | 없음 | Supabase, 테이블, 체크포인터 상태 점검 |

---

## 7. 모델 라우팅

**YAML 기반 동적 모델 선택** (`src/editorial_ai/routing/routing_config.yaml`)

| 노드 | 기본 모델 | 업그레이드 모델 | 조건 |
|------|----------|---------------|------|
| curation_research | gemini-2.5-flash | — | — |
| curation_subtopics | gemini-2.5-flash-lite | — | — |
| editorial_content | gemini-2.5-flash | gemini-2.5-pro | revision_count ≥ 2 |
| review | gemini-2.5-flash | gemini-2.5-pro | revision_count ≥ 2 |

```python
router = get_model_router()
decision = router.resolve("editorial_content", revision_count=2)
# → RoutingDecision(model="gemini-2.5-pro", reason="upgrade:revision>=2")
```

---

## 8. 옵저버빌리티 시스템

### 8.1 토큰 트래킹

**ContextVar 기반 노드별 누적:**
- 각 LLM 호출마다 `record_token_usage()` → prompt/completion/cached tokens 기록
- 노드 완료 시 `harvest_tokens()` → 수집 후 초기화

### 8.2 노드 실행 로깅

**`@node_wrapper` 데코레이터:**
- 모든 노드를 자동 래핑
- 실행 시간, 토큰 사용량, 입출력 상태, 에러 기록
- **Fire-and-forget**: 로깅 실패는 파이프라인에 영향 없음

### 8.3 저장소

- **JSONL 파일**: `data/logs/{thread_id}.jsonl`
- 스레드당 1파일, append-only
- DB 오버헤드 없음

---

## 9. 에러 핸들링 & 복원력

| 패턴 | 설명 |
|------|------|
| Node try-except | 각 노드 레벨에서 예외 포착 → error_log 반환 |
| Retry decorator | API 호출 실패 시 지수 백오프 재시도 (3회) |
| Fallback template | design_spec / layout image 실패 → 기본 템플릿 |
| Output repair loop | JSON 파싱 실패 → Gemini repair (최대 2회, temp=0.0) |
| Circuit breaker | Nano Banana 이미지 모델 404 → 해당 세션 비활성화 |
| Escalation | 리뷰 3회 실패 → pipeline_status="failed" |

---

## 10. 설정 (환경변수)

| 변수 | 필수 | 설명 |
|------|------|------|
| `GOOGLE_API_KEY` | O* | Gemini Developer API 키 |
| `GOOGLE_CLOUD_PROJECT` | O* | GCP 프로젝트 ID (Vertex AI용) |
| `GOOGLE_GENAI_USE_VERTEXAI` | — | Vertex AI 사용 여부 (기본 False) |
| `SUPABASE_URL` | O | Supabase 프로젝트 URL |
| `SUPABASE_SERVICE_ROLE_KEY` | O | 서비스 역할 키 (RLS 바이패스) |
| `DATABASE_URL` | O | PostgreSQL 연결 문자열 (session pooler, port 5432) |
| `ADMIN_API_KEY` | — | API 인증 키 (미설정 시 dev 모드) |
| `LANGSMITH_TRACING` | — | LangSmith 추적 활성화 |
| `LANGSMITH_API_KEY` | — | LangSmith API 키 |

*`GOOGLE_API_KEY` 또는 `GOOGLE_CLOUD_PROJECT` 중 하나 필수

---

## 11. 데이터베이스 스키마

### Supabase 테이블

**editorial_contents** (읽기/쓰기)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| thread_id | string | 파이프라인 실행 ID |
| status | string | pending / approved / published / rejected |
| title | string | 콘텐츠 제목 |
| keyword | string | 주요 키워드 |
| layout_json | JSONB | MagazineLayout 전체 JSON |
| review_summary | string | 리뷰 평가 요약 |
| admin_feedback | string | 관리자 피드백 |
| rejection_reason | string | 거절 사유 |
| created_at | timestamp | 생성일 |
| updated_at | timestamp | 수정일 |
| published_at | timestamp? | 발행일 |

**posts** (읽기 전용)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| image_url | string | 이미지 URL |
| artist_name | string | 아티스트명 |
| group_name | string | 그룹명 |
| context | string | 컨텍스트 |
| view_count | int | 조회수 |
| status | string | active / inactive |

**spots** (포스트 → 솔루션 연결)

**solutions** (상품 데이터)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| title | string | 상품명 |
| thumbnail_url | string | 썸네일 |
| metadata | JSON | keywords, qa_pairs |
| link_type | string | affiliate / direct |

---

## 12. 프로젝트 구조

```
src/editorial_ai/
├── api/
│   ├── app.py                     # FastAPI 앱 (lifespan)
│   ├── deps.py                    # DI (인증, 그래프)
│   ├── schemas.py                 # 요청/응답 스키마
│   └── routes/
│       ├── pipeline.py            # /api/pipeline/*
│       ├── admin.py               # /api/contents/*
│       ├── logs.py                # 로그 엔드포인트
│       └── health.py              # /health
├── nodes/
│   ├── curation.py                # 큐레이션 노드
│   ├── design_spec.py             # 디자인 스펙 노드
│   ├── source.py                  # 소스 노드 (Supabase)
│   ├── editorial.py               # 에디토리얼 노드
│   ├── enrich_from_posts.py       # 실데이터 주입 노드
│   ├── review.py                  # 리뷰 노드 (LLM-as-a-Judge)
│   ├── admin_gate.py              # 관리자 승인 게이트
│   └── publish.py                 # 발행 노드
├── services/
│   ├── curation_service.py        # Gemini + Google Search
│   ├── editorial_service.py       # 4단계 에디토리얼 생성
│   ├── review_service.py          # 하이브리드 평가
│   ├── design_spec_service.py     # 디자인 스펙 생성
│   ├── content_service.py         # CRUD (로컬 JSON)
│   └── supabase_client.py         # Supabase 클라이언트
├── models/
│   ├── editorial.py               # EditorialContent
│   ├── layout.py                  # MagazineLayout, Block 타입들
│   ├── curation.py                # CuratedTopic
│   ├── review.py                  # ReviewResult
│   └── design_spec.py             # DesignSpec
├── prompts/                       # 프롬프트 템플릿
├── rubrics/                       # 적응형 루브릭
├── routing/                       # 모델 라우터 (YAML)
├── observability/                 # 토큰 트래킹 & 로깅
├── caching/                       # 컨텍스트 캐시 (비활성)
├── config.py                      # 설정 관리
├── graph.py                       # 그래프 토폴로지
├── state.py                       # 파이프라인 상태 스키마
├── llm.py                         # LLM 팩토리
└── checkpointer.py                # PostgreSQL 체크포인터
```

---

## 13. 의존성

| 패키지 | 버전 | 역할 |
|--------|------|------|
| langgraph | ≥1.0.9 | 상태 그래프 |
| langgraph-checkpoint-postgres | ≥3.0.4 | 상태 체크포인팅 |
| google-genai | (native) | Gemini API |
| langchain-google-genai | ≥4.2.1 | LangChain 통합 |
| langsmith | ≥0.7.5 | 추적 (선택) |
| supabase | ≥2.28.0 | 데이터 소싱 |
| fastapi | ≥0.115.0 | REST API |
| pydantic | ≥2.12.5 | 스키마 검증 |
| psycopg | ≥3.3.3 | PostgreSQL 드라이버 |
| pyyaml | ≥6.0.3 | 라우팅 설정 |

---

## 14. E2E 워크플로우 예시

```
1. POST /api/pipeline/trigger
   → {seed_keyword: "Jennie Effect", category: "fashion"}
   ← {thread_id: "abc123"}

2. [curation] Gemini + Google Search → 트렌드 리서치
   → CuratedTopic[] (제니 효과, 관련 브랜드/셀럽)

3. [design_spec] → DesignSpec (컬러/타이포그래피/레이아웃)

4. [source] Supabase → posts WHERE artist_name LIKE '%Jennie%'
   → enriched_contexts (이미지, 아티스트, 솔루션)

5. [editorial] Gemini → EditorialContent + Layout Image → MagazineLayout

6. [enrich] 실데이터(이미지/상품) → MagazineLayout 블록에 주입

7. [review] Format 검증 + LLM-as-a-Judge 의미 평가
   → passed: true → admin_gate로 이동

8. [admin_gate] Supabase에 pending 저장 → interrupt() 일시정지

9. Admin: POST /api/contents/{id}/approve

10. [publish] status → "published"

11. GET /api/pipeline/status/abc123
    → {pipeline_status: "published"}
```
