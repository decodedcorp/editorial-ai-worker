# Phase 1: Graph Skeleton + LLM Integration - Research

**Researched:** 2026-02-20
**Domain:** LangGraph StateGraph + Vertex AI (Gemini) integration, Python project scaffolding
**Confidence:** HIGH

## Summary

Phase 1은 전체 파이프라인의 기반 인프라를 구축한다. Python 프로젝트를 uv로 scaffold하고, LangGraph StateGraph로 그래프 스켈레톤(stub nodes + edges)을 정의하여 컴파일 가능한 상태를 만들고, `langchain-google-genai`를 통해 Gemini 2.5 Flash LLM 호출이 동작하는 것을 확인하며, LangSmith 트레이싱을 연결한다.

핵심 기술 스택은 안정적이다. `langgraph>=1.0.9`는 GA 상태이고, `langchain-google-genai>=4.2.1`은 deprecated `ChatVertexAI`를 대체하는 공식 통합 패키지다. LangSmith 트레이싱은 환경변수 설정만으로 자동 활성화된다.

이 Phase에서 가장 중요한 아키텍처 결정은 **lean state schema 설계**다. 여기서 확립한 state 구조가 모든 후속 Phase의 데이터 흐름을 결정하므로, ID/참조 중심의 minimal state를 원칙으로 삼아야 한다.

**Primary recommendation:** `uv init`으로 프로젝트를 생성하고, lean TypedDict state schema + stub nodes로 StateGraph를 컴파일한 뒤, `ChatGoogleGenerativeAI(model="gemini-2.5-flash")`로 LLM 호출을 검증하라. Vertex AI와 Gemini Developer API 두 경로 모두 지원되도록 설계하되, 초기 개발에는 Gemini Developer API 무료 티어를 활용하라.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langgraph` | `>=1.0.9` | StateGraph 기반 멀티에이전트 오케스트레이션 | v1.0 GA (2025.10). 600+ 기업 프로덕션 사용. TypedDict state, conditional edges, checkpointer 내장. |
| `langchain-google-genai` | `>=4.2.1` | LangChain-Gemini 통합 | v4.0+에서 `google-genai` 통합 SDK 기반으로 전환. `ChatVertexAI` deprecated 대체. Vertex AI + Developer API 모두 지원. |
| `langchain-core` | (langgraph 의존성) | LangChain 기본 인터페이스 | langgraph 설치 시 자동 포함. BaseMessage, Runnable 등 핵심 추상화. |
| `pydantic` | `>=2.12.5` | State schema, 구조화 출력 검증 | TypedDict 보완. LLM structured output, FastAPI 응답 모델과 단일 스키마로 통일. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic-settings` | `>=2.8.0` | 환경변수 기반 설정 관리 | `.env` 파일 + 환경변수 통합 로드. 타입 안전한 설정. |
| `python-dotenv` | `>=1.0.0` | `.env` 파일 로드 | 로컬 개발 환경에서 환경변수 자동 로드. |
| `langsmith` | `>=0.3.0` | LangSmith 트레이싱 SDK | 환경변수 설정 시 LangGraph 실행 자동 트레이싱. |

### Dev Dependencies

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ruff` | `>=0.9.0` | Linter + formatter | flake8 + black + isort 통합 대체. 단일 도구. |
| `pytest` | `>=8.3.0` | 테스트 프레임워크 | 단위/통합 테스트. |
| `pytest-asyncio` | `>=0.25.0` | 비동기 테스트 지원 | LangGraph 비동기 호출 테스트. |
| `mypy` | `>=1.14.0` | 정적 타입 체크 | TypedDict/Pydantic 모델 타입 검증. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `langchain-google-genai` | `langchain-google-vertexai` | **사용 금지.** 2026.06 지원 중단 예정. `ChatVertexAI` deprecated. |
| `langgraph` | CrewAI | 상위 추상화. state transition, conditional edge 제어력 부족. HITL 패턴 미지원. |
| `langgraph` | Google ADK | 신생 프레임워크. GCP 결합 강하나 커뮤니티 생태계 부족. |
| `uv` | pip / poetry | uv가 10-100x 빠르고 lockfile 지원 우수. Poetry는 의존성 해석 느림. |

**Installation:**
```bash
# uv 프로젝트 초기화
uv init editorial-ai-worker --python 3.12

# 코어 의존성 추가
uv add langgraph langchain-google-genai pydantic pydantic-settings python-dotenv langsmith

# 개발 의존성 추가
uv add --dev ruff mypy pytest pytest-asyncio
```

## Architecture Patterns

### Recommended Project Structure

```
editorial-ai-worker/
├── src/
│   └── editorial_ai/
│       ├── __init__.py
│       ├── graph.py              # StateGraph 정의 + compile (진입점)
│       ├── state.py              # EditorialPipelineState TypedDict
│       ├── config.py             # Settings (pydantic-settings)
│       ├── llm.py                # LLM 인스턴스 팩토리
│       ├── nodes/                # 그래프 노드 함수들
│       │   ├── __init__.py
│       │   ├── curation.py       # Phase 3에서 구현
│       │   ├── editorial.py      # Phase 4에서 구현
│       │   ├── review.py         # Phase 6에서 구현
│       │   ├── admin_gate.py     # Phase 7에서 구현
│       │   └── publish.py        # Phase 7에서 구현
│       └── services/             # 외부 서비스 래퍼
│           ├── __init__.py
│           └── (Phase 2+에서 추가)
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # 공통 fixture
│   ├── test_graph.py             # 그래프 컴파일 + 실행 테스트
│   ├── test_state.py             # State schema 테스트
│   └── test_llm.py               # LLM 호출 테스트
├── .env.example                  # 환경변수 템플릿
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

**구조 결정 근거:**
- `src/editorial_ai/` 레이아웃: Python 패키징 표준. `src/` prefix로 import 실수 방지.
- `nodes/` 디렉토리: 각 노드를 개별 파일로 분리. Phase별 독립 구현 가능.
- `services/` 디렉토리: 외부 API(Supabase, Perplexity) 래퍼. 노드와 서비스 관심사 분리.
- `graph.py`를 진입점으로: LangGraph 공식 예제 구조(`src/agent/graph.py`)와 일치.

**Confidence: MEDIUM** - LangGraph 공식 템플릿(`langchain-ai/new-langgraph-project`)의 `src/agent/` 구조를 기반으로 하되, 멀티에이전트 파이프라인에 맞게 `nodes/`와 `services/` 확장. 공식 문서에는 대형 프로젝트 구조에 대한 명확한 권장이 없으므로, 커뮤니티 패턴과 LangGraph 공식 예제를 결합한 추론.

### Pattern 1: TypedDict State with Lean Principle

**What:** State를 TypedDict로 정의하되, ID/참조만 저장하고 전체 페이로드는 외부 저장소에 둔다.
**When to use:** 항상. 이것이 Phase 1에서 확립하는 핵심 원칙.
**Why:** checkpoint state bloat 방지 (Pitfall #2). 매 노드 전환마다 전체 state가 직렬화/저장됨.

```python
# Source: LangGraph official docs + ARCHITECTURE.md patterns
from typing import TypedDict, Annotated, Optional, Literal
import operator

class EditorialPipelineState(TypedDict):
    """파이프라인 공유 상태. Lean 원칙: ID/참조만, 페이로드는 외부 저장."""

    # --- Curation Phase ---
    curation_input: dict                  # 트리거 파라미터 (week, filters)
    curated_topics: list[dict]            # [{celeb_id, product_id, angle, trend_keywords}]

    # --- Source Phase ---
    enriched_contexts: list[dict]         # [{topic, sources, facts, overlap_score}]

    # --- Editorial Phase ---
    current_draft_id: Optional[str]       # Supabase draft row ID (lean: ID만)
    tool_calls_log: Annotated[list[dict], operator.add]  # 누적: tool 사용 로그

    # --- Review Phase ---
    review_result: Optional[dict]         # {passed, feedback, scores}
    revision_count: int                   # 피드백 루프 카운터
    feedback_history: Annotated[list[dict], operator.add]  # 누적: 리뷰 피드백

    # --- Admin Gate ---
    admin_decision: Optional[Literal["approved", "rejected", "revision_requested"]]
    admin_feedback: Optional[str]

    # --- Pipeline Meta ---
    pipeline_status: Literal[
        "curating", "sourcing", "drafting", "reviewing",
        "awaiting_approval", "published", "failed"
    ]
    error_log: Annotated[list[str], operator.add]  # 누적: 에러 로그
```

**Annotated reducer 사용 기준:**
- `operator.add` reducer: 누적이 필요한 필드만 (error_log, tool_calls_log, feedback_history)
- 나머지 필드: last-write-wins (기본값). 각 노드가 자기 담당 필드를 덮어씀.

**Confidence: HIGH** - `Annotated[list, operator.add]` 패턴은 LangGraph 공식 문서에서 직접 확인. TypedDict state 정의는 LangGraph의 핵심 API.

### Pattern 2: Stub Node Pattern for Incremental Build

**What:** 모든 노드를 stub(빈 함수)으로 먼저 정의하고, Phase별로 실제 구현으로 교체.
**When to use:** Phase 1에서 그래프 스켈레톤 구축 시.
**Why:** 그래프 토폴로지를 먼저 검증. 컴파일 에러를 조기 발견.

```python
# Source: LangGraph docs - graph-api
from langgraph.graph import StateGraph, START, END

def stub_curation(state: EditorialPipelineState) -> dict:
    """Stub: Phase 3에서 구현."""
    return {"pipeline_status": "sourcing", "curated_topics": []}

def stub_source(state: EditorialPipelineState) -> dict:
    """Stub: Phase 3에서 구현."""
    return {"pipeline_status": "drafting", "enriched_contexts": []}

def stub_editorial(state: EditorialPipelineState) -> dict:
    """Stub: Phase 4에서 구현."""
    return {"pipeline_status": "reviewing", "current_draft_id": None}

def stub_review(state: EditorialPipelineState) -> dict:
    """Stub: Phase 6에서 구현."""
    return {"pipeline_status": "awaiting_approval", "review_result": {"passed": True}}

def stub_admin_gate(state: EditorialPipelineState) -> dict:
    """Stub: Phase 7에서 구현."""
    return {"pipeline_status": "published", "admin_decision": "approved"}

def stub_publish(state: EditorialPipelineState) -> dict:
    """Stub: Phase 7에서 구현."""
    return {"pipeline_status": "published"}

# --- Graph Construction ---
builder = StateGraph(EditorialPipelineState)

builder.add_node("curation", stub_curation)
builder.add_node("source", stub_source)
builder.add_node("editorial", stub_editorial)
builder.add_node("review", stub_review)
builder.add_node("admin_gate", stub_admin_gate)
builder.add_node("publish", stub_publish)

builder.add_edge(START, "curation")
builder.add_edge("curation", "source")
builder.add_edge("source", "editorial")
builder.add_edge("editorial", "review")

# Conditional: Review 결과에 따른 라우팅
def route_after_review(state: EditorialPipelineState) -> str:
    review = state.get("review_result", {})
    if review.get("passed"):
        return "approve"
    if state.get("revision_count", 0) >= 3:
        return "fail"
    return "revision"

builder.add_conditional_edges(
    "review",
    route_after_review,
    {"revision": "editorial", "approve": "admin_gate", "fail": END}
)

# Conditional: Admin 결정에 따른 라우팅
def route_after_admin(state: EditorialPipelineState) -> str:
    decision = state.get("admin_decision", "rejected")
    if decision == "approved":
        return "approved"
    if decision == "revision_requested":
        return "revision_requested"
    return "rejected"

builder.add_conditional_edges(
    "admin_gate",
    route_after_admin,
    {"approved": "publish", "revision_requested": "editorial", "rejected": END}
)

builder.add_edge("publish", END)

# --- Compile ---
graph = builder.compile()
```

**Confidence: HIGH** - StateGraph API(`add_node`, `add_edge`, `add_conditional_edges`, `compile`)는 LangGraph 공식 문서에서 확인.

### Pattern 3: LLM Factory with Backend Flexibility

**What:** LLM 인스턴스를 팩토리 함수로 생성하여 Gemini Developer API와 Vertex AI 백엔드를 환경변수로 전환 가능하게 한다.
**When to use:** LLM 호출이 필요한 모든 노드.
**Why:** 로컬 개발(Developer API 무료 티어) → 프로덕션(Vertex AI)을 코드 변경 없이 전환.

```python
# Source: langchain-google-genai official docs
from langchain_google_genai import ChatGoogleGenerativeAI
from editorial_ai.config import settings

def create_llm(
    model: str = "gemini-2.5-flash",
    temperature: float = 0.7,
) -> ChatGoogleGenerativeAI:
    """LLM 인스턴스 팩토리. 환경변수로 백엔드 자동 결정."""
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        # vertexai 백엔드 자동 결정 로직:
        # - GOOGLE_GENAI_USE_VERTEXAI=true → Vertex AI
        # - project 파라미터 설정 → Vertex AI
        # - GOOGLE_API_KEY만 설정 → Gemini Developer API
        project=settings.gcp_project_id,  # None이면 Developer API 사용
        location=settings.gcp_location,    # 기본값 "us-central1"
    )
```

**Confidence: HIGH** - `ChatGoogleGenerativeAI` 생성자의 `project`, `vertexai`, `location` 파라미터와 자동 백엔드 결정 로직은 공식 LangChain 문서에서 확인.

### Anti-Patterns to Avoid

- **Fat State (God State):** state에 전체 article JSON, 검색 결과 전문 등을 저장하지 마라. 매 노드 전환마다 checkpoint에 전체가 복사됨. `current_draft_id`(ID만) 저장하고 full payload는 Supabase에.
- **Unbounded Message Accumulation:** `messages: Annotated[list, add_messages]` 사용 시 트리밍 없이 무한 누적 금지. 이 Phase에서는 `messages` 필드를 state에 넣지 않는다. 각 노드가 자체 LLM 호출 시 독립적 컨텍스트 사용.
- **Shared LLM Instance:** 모든 노드가 동일 LLM 인스턴스 + 동일 system prompt 사용 금지. 노드별 독립 LLM 인스턴스 + 전용 system prompt.
- **MemorySaver in Non-Test Code:** `MemorySaver`는 테스트 전용. 서버 재시작 시 상태 소실.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph 오케스트레이션 | Custom state machine | `langgraph.StateGraph` | Conditional edges, checkpointing, interrupt 내장. 직접 구현 시 수개월 소요. |
| LLM 호출 추상화 | Raw `google-genai` SDK wrapper | `ChatGoogleGenerativeAI` | Retry, streaming, structured output, tool calling 내장. LangGraph와 자동 통합. |
| LLM 트레이싱 | Custom logging/tracing | LangSmith | 환경변수만 설정하면 LangGraph 실행 자동 추적. Token 사용량, 지연시간, 에이전트 라우팅 결정 모두 기록. |
| 환경변수 관리 | Raw `os.environ` | `pydantic-settings` | 타입 검증, 기본값, `.env` 로드 통합. 설정 오류 조기 발견. |
| State 영속화 | Custom DB checkpointing | `langgraph-checkpoint-postgres` (Phase 2) | 공식 체크포인터. interrupt/resume, 상태 복원 보장. |

**Key insight:** Phase 1에서는 checkpointer를 설정하지 않는다 (`MemorySaver` 테스트용으로만). Phase 2에서 Postgres checkpointer를 추가. 하지만 state schema는 Phase 1에서 lean 원칙으로 설계해야 나중에 checkpointer 연결 시 bloat가 없다.

## Common Pitfalls

### Pitfall 1: 잘못된 SDK 선택 (ChatVertexAI 사용)

**What goes wrong:** `langchain-google-vertexai`의 `ChatVertexAI`로 구축 후 deprecated 발견. 2026.06 이후 Gemini 지원 중단.
**Why it happens:** 기존 튜토리얼/예제가 여전히 `ChatVertexAI` 참조.
**How to avoid:** `langchain-google-genai>=4.2.1`의 `ChatGoogleGenerativeAI`만 사용. import 시 `from langchain_google_genai import ChatGoogleGenerativeAI` 확인.
**Warning signs:** `langchain-google-vertexai` 패키지가 `pyproject.toml`에 있으면 즉시 제거.
**Confidence: HIGH** - GitHub Discussion #1422에서 공식 확인.

### Pitfall 2: Checkpoint State Bloat 설계

**What goes wrong:** State에 전체 article content, 검색 결과, LLM 응답을 직접 저장. 매 노드 전환마다 전체 state가 checkpoint로 직렬화되어 DB bloat 발생.
**Why it happens:** 개발 초기에는 문제가 안 보임. 데이터가 쌓이면서 서서히 악화.
**How to avoid:** Phase 1에서 lean state 원칙 확립. `current_draft_id` (ID) 저장, full payload는 Supabase에. 이 원칙을 코드 리뷰 체크리스트에 추가.
**Warning signs:** State 필드에 `str` 타입으로 긴 텍스트 저장, `dict` 타입으로 중첩 구조 저장.
**Confidence: HIGH** - LangGraph checkpointing 공식 문서 + 다수 커뮤니티 경험 보고.

### Pitfall 3: LangSmith 환경변수 혼동

**What goes wrong:** `LANGCHAIN_TRACING_V2` vs `LANGSMITH_TRACING`, `LANGCHAIN_API_KEY` vs `LANGSMITH_API_KEY` 혼용.
**Why it happens:** LangChain/LangSmith 문서가 버전별로 다른 변수명을 사용.
**How to avoid:** 두 세트 모두 동작하지만, 현재 공식 quickstart는 `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` 사용. 일관성을 위해 하나를 선택하고 프로젝트 전체에서 통일.
**Warning signs:** 트레이싱이 LangSmith 대시보드에 나타나지 않을 때.
**Confidence: MEDIUM** - 공식 문서 간 불일치 확인. 두 변수 세트 모두 작동하나 `LANGSMITH_*`가 최신 quickstart에서 사용됨.

### Pitfall 4: Gemini Developer API vs Vertex AI 혼동

**What goes wrong:** API 키와 프로젝트 설정을 동시에 하면 어느 백엔드가 사용되는지 불명확. 과금 경로 혼란.
**Why it happens:** `ChatGoogleGenerativeAI`는 여러 파라미터로 백엔드를 자동 결정. `project` 파라미터가 설정되면 Vertex AI로 라우팅되지만, API key만 있으면 Developer API 사용.
**How to avoid:**
- 로컬 개발: `GOOGLE_API_KEY`만 설정 → Developer API 무료 티어 사용
- 프로덕션: `GOOGLE_GENAI_USE_VERTEXAI=true` + `GOOGLE_CLOUD_PROJECT` + ADC → Vertex AI + 클라우드 과금
- `.env.example`에 두 경로를 명확히 문서화
**Warning signs:** 예상치 못한 과금, 또는 무료로 쓰려 했는데 Vertex AI 과금 발생.
**Confidence: HIGH** - 공식 LangChain Google GenAI 문서에서 백엔드 결정 로직 확인.

### Pitfall 5: Python 프로젝트 구조 미숙

**What goes wrong:** `src/` 레이아웃 없이 루트에 모듈 배치. 테스트에서 import 경로 혼란. uv lockfile 미커밋.
**Why it happens:** 빠른 프로토타이핑에서 구조 건너뜀.
**How to avoid:** `uv init`으로 시작하고, `src/editorial_ai/` 구조 사용. `uv.lock`을 git에 커밋.
**Warning signs:** `ModuleNotFoundError` 빈번 발생. 테스트와 소스 코드의 import 경로 불일치.
**Confidence: MEDIUM** - uv 공식 문서 + Python 패키징 가이드 기반 추론.

## Code Examples

### Example 1: 환경변수 설정 (`.env.example`)

```bash
# === LLM Provider ===
# Option A: Gemini Developer API (무료 티어, 로컬 개발용)
GOOGLE_API_KEY=your-google-api-key

# Option B: Vertex AI (프로덕션, Google AI Ultra 크레딧 활용)
# GOOGLE_GENAI_USE_VERTEXAI=true
# GOOGLE_CLOUD_PROJECT=your-gcp-project-id
# GOOGLE_CLOUD_LOCATION=us-central1

# === LangSmith Tracing ===
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=editorial-ai-worker
```

### Example 2: Settings with pydantic-settings

```python
# Source: pydantic-settings official docs
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """애플리케이션 설정. .env 파일 또는 환경변수에서 로드."""

    # LLM
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    gcp_project_id: Optional[str] = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")
    gcp_location: str = Field(default="us-central1", alias="GOOGLE_CLOUD_LOCATION")
    google_genai_use_vertexai: Optional[bool] = Field(
        default=None, alias="GOOGLE_GENAI_USE_VERTEXAI"
    )
    default_model: str = "gemini-2.5-flash"

    # LangSmith
    langsmith_tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")
    langsmith_api_key: Optional[str] = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(
        default="editorial-ai-worker", alias="LANGSMITH_PROJECT"
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

### Example 3: LLM 호출 검증 스크립트

```python
# Source: langchain-google-genai official docs
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
)

# 기본 호출 테스트
response = llm.invoke("안녕하세요, 패션 트렌드에 대해 간단히 설명해주세요.")
print(response.content)
```

### Example 4: Structured Output with Pydantic

```python
# Source: langchain-google-genai official docs
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI


class TrendSummary(BaseModel):
    keyword: str
    category: str
    relevance_score: float


llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
structured_llm = llm.with_structured_output(TrendSummary)

result = structured_llm.invoke(
    "2026년 봄 패션 트렌드 키워드 하나를 JSON으로 반환해주세요."
)
# result는 TrendSummary 인스턴스
```

### Example 5: 그래프 컴파일 + 실행 테스트

```python
# Source: LangGraph official docs
import pytest
from editorial_ai.graph import graph
from langgraph.graph import StateGraph


def test_graph_compiles():
    """그래프가 에러 없이 컴파일되는지 확인."""
    assert graph is not None
    # graph는 이미 compile()된 상태


def test_graph_stub_execution():
    """Stub 노드로 그래프가 끝까지 실행되는지 확인."""
    initial_state = {
        "curation_input": {"week": "2026-W08"},
        "curated_topics": [],
        "enriched_contexts": [],
        "current_draft_id": None,
        "tool_calls_log": [],
        "review_result": None,
        "revision_count": 0,
        "feedback_history": [],
        "admin_decision": None,
        "admin_feedback": None,
        "pipeline_status": "curating",
        "error_log": [],
    }
    result = graph.invoke(initial_state)
    assert result["pipeline_status"] == "published"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ChatVertexAI` (`langchain-google-vertexai`) | `ChatGoogleGenerativeAI` (`langchain-google-genai>=4.0`) | 2025.10 (v4.0.0) | 필수 마이그레이션. 2026.06 이후 `ChatVertexAI`에서 Gemini 미지원. |
| `google-cloud-aiplatform` SDK | `google-genai` 통합 SDK | 2025.05 GA | 단일 SDK로 Developer API + Vertex AI 모두 지원. |
| `LANGCHAIN_TRACING_V2` + `LANGCHAIN_API_KEY` | `LANGSMITH_TRACING` + `LANGSMITH_API_KEY` | 2025 (점진적) | 두 세트 모두 동작. 최신 quickstart는 `LANGSMITH_*` 사용. |
| pip / poetry | uv | 2025-2026 (표준화 진행) | 10-100x 빠른 의존성 관리. `uv.lock`으로 결정적 빌드. |
| `langgraph` pre-1.0 | `langgraph>=1.0.8` | 2025.10 GA | 안정 API. `compile()`, `interrupt()`, `Command()` 정식 지원. |

**Deprecated/outdated:**
- `langchain-google-vertexai` / `ChatVertexAI`: 2026.06 이후 Gemini 미지원. 즉시 `langchain-google-genai`로 전환 필요.
- `google-cloud-aiplatform` 직접 사용: `google-genai` SDK가 대체. LangChain 통합은 `langchain-google-genai`가 래핑.
- LangServe: deprecated. LangGraph Platform 또는 FastAPI 사용.

## Open Questions

1. **Google AI Ultra 크레딧과 Gemini Developer API의 관계**
   - What we know: Google AI Ultra ($100/월 GCP 크레딧 포함)는 Vertex AI 과금에 적용됨. Gemini Developer API 무료 티어는 별도.
   - What's unclear: Ultra 크레딧이 Developer API 유료 티어에도 적용되는지, 또는 반드시 Vertex AI(`vertexai=True`)로 라우팅해야 하는지.
   - Recommendation: 초기 개발에는 Developer API 무료 티어(`GOOGLE_API_KEY`만) 사용. 프로덕션에서는 Vertex AI(`GOOGLE_GENAI_USE_VERTEXAI=true`) 설정하여 GCP 크레딧 활용. 두 경로 모두 코드 변경 없이 환경변수로 전환 가능하도록 설계.

2. **LangSmith 환경변수 명명 통일**
   - What we know: `LANGSMITH_TRACING` + `LANGSMITH_API_KEY`(최신 quickstart)와 `LANGCHAIN_TRACING_V2` + `LANGCHAIN_API_KEY`(레거시 support 문서) 모두 동작.
   - What's unclear: 어느 것이 장기적으로 유지될지.
   - Recommendation: `LANGSMITH_TRACING` + `LANGSMITH_API_KEY` 사용 (최신 공식 문서 기준). `pydantic-settings`에서 alias로 두 변수명 모두 수용하는 것도 가능.

3. **`location` 기본값: `"global"` vs `"us-central1"`**
   - What we know: 공식 LangChain reference는 `location` 기본값을 `"global"`로 표시. 많은 예제에서는 `"us-central1"` 사용.
   - What's unclear: Vertex AI에서 `"global"` 리전이 Gemini 2.5 Flash를 지원하는지.
   - Recommendation: `"us-central1"`을 명시적으로 설정. 가장 많은 모델이 지원되는 리전.

## Sources

### Primary (HIGH confidence)
- [LangGraph Graph API - Official Docs](https://docs.langchain.com/oss/python/langgraph/graph-api) - StateGraph, add_node, add_edge, compile API
- [ChatGoogleGenerativeAI - Official Docs](https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai) - 생성자 파라미터, Vertex AI 설정, structured output
- [ChatGoogleGenerativeAI - API Reference](https://reference.langchain.com/python/integrations/langchain_google_genai/ChatGoogleGenerativeAI/) - 생성자 파라미터 상세
- [langchain-google-genai 4.0.0 Release Discussion](https://github.com/langchain-ai/langchain-google/discussions/1422) - ChatVertexAI deprecation 공식 확인
- [LangSmith Observability Quickstart](https://docs.langchain.com/langsmith/observability-quickstart) - 환경변수 설정
- [LangSmith Trace with LangGraph](https://docs.langchain.com/langsmith/trace-with-langgraph) - LangGraph 자동 트레이싱
- [LangSmith API Key Setup - Support](https://support.langchain.com/articles/3567245886-how-do-i-set-up-langsmith-api-key-environment-variables) - LANGCHAIN_API_KEY 명명
- [langgraph PyPI](https://pypi.org/project/langgraph/) - v1.0.9 확인
- [langchain-google-genai PyPI](https://pypi.org/project/langchain-google-genai/) - v4.2.1 확인
- [Gemini Developer API Pricing](https://ai.google.dev/gemini-api/docs/pricing) - 무료 티어, 2.5 Flash 가격
- [LangGraph Application Structure - Official Docs](https://docs.langchain.com/oss/python/langgraph/application-structure) - 프로젝트 구조 가이드
- [new-langgraph-project Template](https://github.com/langchain-ai/new-langgraph-project) - 공식 프로젝트 템플릿
- [uv Project Guide](https://docs.astral.sh/uv/guides/projects/) - uv init, pyproject.toml

### Secondary (MEDIUM confidence)
- [Google AI Ultra Developer Benefits](https://blog.google/innovation-and-ai/technology/developers-tools/gdp-premium-ai-pro-ultra/) - Google AI Ultra $100/월 GCP 크레딧
- [LangGraph Best Practices (Swarnendu De)](https://www.swarnendu.de/blog/langgraph-best-practices/) - 프로덕션 패턴
- [Scaling AI Agents: Modular Architecture for LangGraph (Medium)](https://medium.com/@yasin162001/scaling-ai-agents-beyond-notebooks-a-modular-architecture-for-langgraph-in-production-4711764de464) - 프로젝트 구조 패턴

### Tertiary (LOW confidence)
- Google AI Ultra 크레딧이 Developer API 유료 티어에 적용되는지 여부 - 공식 확인 불가, 검증 필요

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - 모든 패키지 버전 PyPI에서 확인. API 패턴 공식 문서에서 검증.
- Architecture: HIGH (state/graph) / MEDIUM (프로젝트 구조) - state/graph는 공식 API. 프로젝트 구조는 공식 템플릿 기반 추론.
- Pitfalls: HIGH - deprecated SDK, state bloat 모두 공식 소스에서 확인. LangSmith 환경변수 혼동은 공식 문서 간 불일치로 직접 확인.

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (30 days - 안정 기술 스택, major 변경 가능성 낮음)
