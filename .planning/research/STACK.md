# Technology Stack

**Project:** Editorial AI Worker (Fashion editorial content auto-generation)
**Researched:** 2026-02-20
**Overall Confidence:** MEDIUM-HIGH

---

## Recommended Stack

### LLM Orchestration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `langgraph` | `>=1.0.8` | Multi-agent graph orchestration | v1.0 GA. Industry standard for stateful multi-agent pipelines. Supervisor pattern fits Curation->Editorial->Source->Review->Publish flow. Google officially supports LangGraph on Vertex AI Agent Engine. | HIGH |
| `langgraph-checkpoint-postgres` | `>=2.0.0` | Durable state persistence | Official Postgres checkpointer. Works directly with Supabase's PostgreSQL. Enables pause/resume, human-in-the-loop review steps. | HIGH |
| `langgraph-prebuilt` | `>=0.2.0` | Pre-built agent patterns (supervisor, etc.) | Provides `create_react_agent`, supervisor templates. Reduces boilerplate for standard patterns. | MEDIUM |

**Architecture Pattern: Supervisor (not Swarm)**

Use the **supervisor pattern** for this pipeline. Rationale:
- The editorial pipeline is a **deterministic, sequential workflow** (Curation -> Editorial -> Source -> Review -> Publish), not a free-form collaborative swarm
- Supervisor provides predictable orchestration with clear handoff points
- Human-in-the-loop review step requires controlled state management that supervisor handles natively
- Swarm's token savings (~20-30% fewer tokens) don't justify the loss of centralized control and observability for an editorial quality pipeline
- Admin dashboard needs visibility into pipeline state -- supervisor's centralized state is easier to expose

### LLM Provider

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `langchain-google-genai` | `>=4.1.2` | LangChain <-> Gemini integration | v4.0+ uses the new consolidated `google-genai` SDK. Replaces deprecated `langchain-google-vertexai` / `ChatVertexAI`. Use `ChatGoogleGenerativeAI` with `project` param for Vertex AI access. | HIGH |
| `google-genai` | `>=1.62.0` | Underlying Google Gen AI SDK | GA since May 2025. Unified SDK for both Gemini Developer API and Vertex AI. Installed as dependency of `langchain-google-genai`. | HIGH |

**Model Selection:**

| Model | Use Case | Why |
|-------|----------|-----|
| `gemini-2.5-flash` | Primary editorial generation (all 5 skills) | GA, stable. Best cost/quality ratio for structured content generation. Fast enough for batch editorial pipelines. |
| `gemini-2.5-flash-lite` | Curation agent, classification, routing | 1.5x faster than 2.0 Flash at lower cost. Ideal for lightweight decision-making tasks (trend filtering, content classification). |
| `gemini-2.0-flash` | Fallback model | Still supported, use as fallback if 2.5 has issues. |

**Do NOT use:**
- `gemini-3-flash` -- Public preview only (as of Feb 2026). Not stable enough for production editorial content.
- `gemini-2.5-pro` -- Overkill for structured content generation. 2.5-flash handles editorial tasks well at fraction of cost.
- `ChatVertexAI` from `langchain-google-vertexai` -- **Deprecated** as of v3.2.0. Will be removed June 2026. Use `ChatGoogleGenerativeAI` from `langchain-google-genai` instead.

### Embeddings & Vector Search

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `gemini-embedding-001` | (model, not package) | Text embeddings for semantic search | Google's SOTA embedding model. 3072-dimensional vectors. Top of MTEB multilingual leaderboard. Available via same `google-genai` SDK. | HIGH |
| Supabase pgvector | (Postgres extension) | Vector storage and similarity search | Already using Supabase for DB. pgvector with HNSW indexing keeps embeddings co-located with relational data. No need for a separate vector DB. | HIGH |

**Do NOT use:**
- Pinecone / Weaviate / Qdrant -- Unnecessary external vector DB when Supabase pgvector handles the scale (fashion editorial content is not billions of vectors). Adds complexity, cost, and another service to manage.
- `text-embedding-005` / `text-multilingual-embedding-002` -- Older Google embedding models. `gemini-embedding-001` supersedes them with better performance.
- OpenAI embeddings -- Vendor lock-in to a second LLM provider. Google embeddings work seamlessly with Vertex AI billing.

### Research & Source Finding

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Perplexity Sonar API | `sonar` model | Trend research, source finding | Purpose-built for web research with citations. $1/M tokens (input+output) is cost-effective. Citation tokens are now free (2026 update). | MEDIUM |
| Perplexity Sonar Pro | `sonar-pro` model | Deep editorial research when needed | $3/$15 per M tokens (in/out). Use selectively for high-quality sourced research that needs deeper analysis. | MEDIUM |

**Do NOT use:**
- `sonar-deep-research` -- $2/$8 per M tokens and designed for multi-step research reports. Overkill for fashion trend sourcing where `sonar` or `sonar-pro` suffice.
- `sonar-reasoning-pro` -- Reasoning model, not needed for factual web search tasks.
- Google Search API + scraping -- Perplexity handles search+summarization in one call. Building your own search pipeline is reinventing the wheel.

### Database & Backend Services

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `supabase` (Python) | `>=2.24.0` | Supabase client for Python | Official Python SDK. Handles auth, DB queries, realtime, storage. | MEDIUM |
| Supabase PostgreSQL | (managed) | Primary database | Relational data (articles, pipeline runs, admin state) + pgvector for embeddings in one DB. Row Level Security for multi-tenant admin access. | HIGH |
| Supabase Edge Functions | (managed) | Webhooks, lightweight triggers | Use for webhook receivers (e.g., publish triggers) and lightweight async tasks. Not for heavy LLM pipeline work. | MEDIUM |

### API / Backend Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `fastapi` | `>=0.129.0` | HTTP API for admin dashboard & pipeline triggers | Industry standard for Python async APIs. Native Pydantic integration (structured output models reuse). Excellent for exposing pipeline status, triggering runs, serving Layout JSON. | HIGH |
| `uvicorn` | `>=0.34.0` | ASGI server | Standard production server for FastAPI. | HIGH |

**Deployment Target: Google Cloud Run (not Cloudflare Workers)**

Rationale:
- Multi-agent LLM pipelines are **long-running** (minutes, not milliseconds). Cloudflare Workers have CPU time limits (30s free, 15min paid) that constrain complex editorial pipelines.
- Cloud Run supports **up to 60-minute request timeouts** and background tasks.
- Vertex AI (Gemini) calls from Cloud Run benefit from **same-network latency** within GCP.
- Cloud Run has native **async/background processing** support via Cloud Tasks or Pub/Sub.
- Cloudflare Workers + Workflows *could* work but adds unnecessary complexity for a pipeline that naturally fits Cloud Run's container model.

**Do NOT use:**
- Cloudflare Workers as primary compute -- Despite the repo name "worker", the multi-agent pipeline needs long execution times and heavy state management that Cloud Run handles better. Use Cloudflare only if you need an edge proxy/gateway in front of Cloud Run.
- AWS Lambda -- Same timeout constraints as CF Workers. Also, Vertex AI is on GCP, so cross-cloud latency is wasteful.
- Django/Flask -- No async support comparable to FastAPI. LangGraph is async-native; the API layer should be too.

### Structured Output & Validation

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `pydantic` | `>=2.12.5` | Schema definition, LLM output validation | Defines Layout JSON schema, editorial content models, pipeline state. Used by both LangGraph (state) and FastAPI (API models). Single source of truth for all data shapes. | HIGH |
| `pydantic-settings` | `>=2.8.0` | Configuration management | Type-safe config from env vars. Replaces raw `os.environ` access. | HIGH |

### Development & Tooling

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `uv` | `>=0.6.0` | Package manager & project tooling | 10-100x faster than pip. Native `pyproject.toml` support. Deterministic lockfiles. Becoming Python ecosystem standard. | HIGH |
| `ruff` | `>=0.9.0` | Linter + formatter | Replaces flake8 + black + isort. Single tool, written in Rust, extremely fast. | HIGH |
| `pytest` | `>=8.3.0` | Testing framework | Standard. Use with `pytest-asyncio` for async LangGraph tests. | HIGH |
| `pytest-asyncio` | `>=0.25.0` | Async test support | LangGraph is async-native. Tests need async support. | HIGH |
| `mypy` | `>=1.14.0` | Static type checking | Catches Pydantic model mismatches, LangGraph state errors at dev time. | MEDIUM |
| `python-dotenv` | `>=1.0.0` | Local env var loading | Load `.env` for local development. Not used in production (Cloud Run injects env vars). | HIGH |

### Observability & Monitoring

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| LangSmith | (SaaS) | LLM tracing & debugging | Native LangGraph integration. Traces every agent step, token usage, latency. Essential for debugging multi-agent pipelines. Free tier available. | HIGH |
| `langsmith` | `>=0.3.0` | LangSmith Python SDK | Auto-instruments LangGraph. Set `LANGCHAIN_TRACING_V2=true` and it captures everything. | HIGH |

**Do NOT use:**
- Custom logging for LLM traces -- LangSmith provides structured tracing purpose-built for LangGraph. Rolling your own is weeks of wasted effort.
- OpenTelemetry alone -- Good for infra metrics, but lacks LLM-specific tracing (token counts, prompt/response pairs, agent routing decisions). Use alongside LangSmith, not instead of it.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not Alternative |
|----------|-------------|-------------|---------------------|
| Agent Framework | LangGraph | CrewAI | CrewAI is higher-level abstraction -- good for simple role-based crews but less control over state transitions, conditional routing, and human-in-the-loop patterns needed for editorial review. |
| Agent Framework | LangGraph | Google ADK (Agent Development Kit) | Newer, less mature. Tighter GCP coupling but less community ecosystem. LangGraph has broader adoption (600+ companies in production). |
| Agent Framework | LangGraph | AutoGen | Microsoft-oriented. Weaker Vertex AI integration. More suited for conversational multi-agent, not pipeline orchestration. |
| Vector DB | Supabase pgvector | Pinecone | Separate managed service adds cost and complexity. pgvector is sufficient for fashion editorial scale (thousands to low millions of vectors, not billions). |
| Embeddings | gemini-embedding-001 | OpenAI text-embedding-3-large | Adds second vendor, second billing relationship. Google embeddings are competitive (top MTEB scores) and unified with Vertex AI billing. |
| API Framework | FastAPI | LangServe | LangServe is deprecated in favor of LangGraph Platform. FastAPI gives full control and is not coupled to LangChain's deployment choices. |
| Deployment | Cloud Run | Vertex AI Agent Engine | Agent Engine is managed but opinionated. Cloud Run gives more flexibility for custom admin dashboard, webhook integrations, and non-LLM endpoints. |
| Research API | Perplexity Sonar | Tavily | Perplexity has better citation quality and is purpose-built for research. Tavily is simpler but less capable for editorial-quality sourcing. |
| Package Manager | uv | pip / poetry | uv is dramatically faster, has better lockfile support, and is converging as the Python standard. Poetry is slower and has dependency resolution issues at scale. |

---

## Full Dependency List

```bash
# Core orchestration
langgraph>=1.0.8
langgraph-checkpoint-postgres>=2.0.0
langgraph-prebuilt>=0.2.0

# LLM provider
langchain-google-genai>=4.1.2
# google-genai is pulled in as transitive dependency

# API
fastapi>=0.129.0
uvicorn[standard]>=0.34.0

# Database
supabase>=2.24.0
psycopg[binary]>=3.2.0   # For langgraph-checkpoint-postgres

# Validation & config
pydantic>=2.12.5
pydantic-settings>=2.8.0

# HTTP client (for Perplexity API)
httpx>=0.28.0

# Observability
langsmith>=0.3.0

# Environment
python-dotenv>=1.0.0
```

```bash
# Dev dependencies
ruff>=0.9.0
mypy>=1.14.0
pytest>=8.3.0
pytest-asyncio>=0.25.0
```

### pyproject.toml (uv)

```toml
[project]
name = "editorial-ai-worker"
version = "0.1.0"
requires-python = ">=3.12"

[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "TCH"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

---

## Architecture Decision: Python Version

**Use Python 3.12+**

- LangGraph requires Python >=3.10
- `google-genai` supports 3.9-3.13
- Python 3.12 offers significant performance improvements (10-15% faster) over 3.11
- Cloud Run supports Python 3.12 containers natively
- Python 3.13 is available but some libraries may not fully support it yet

---

## Key Integration Notes

### LangGraph + Gemini via langchain-google-genai 4.x

The critical migration: `langchain-google-vertexai` with `ChatVertexAI` is **deprecated**. The new path is:

```python
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    project="your-gcp-project",        # This routes through Vertex AI
    location="us-central1",
    temperature=0.7,
)
```

This uses `google-genai` under the hood and supports all Vertex AI features (quotas, VPC, IAM) while using the newer, maintained SDK.

### Structured Output Pattern

```python
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI

class EditorialSection(BaseModel):
    headline: str
    body: str
    tone: str
    sources: list[str]

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", project="...")
structured_llm = llm.with_structured_output(EditorialSection)
```

Pydantic models define the Layout JSON schema. Same models validate LLM output AND serve as FastAPI response types. Single source of truth.

### LangGraph Checkpoint with Supabase

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# Use Supabase's direct Postgres connection string
async with AsyncPostgresSaver.from_conn_string(
    "postgresql://postgres:password@db.xxx.supabase.co:5432/postgres"
) as checkpointer:
    await checkpointer.setup()
    graph = workflow.compile(checkpointer=checkpointer)
```

Use the **direct connection string** (port 5432), not the pooled connection (port 6543), as the checkpointer manages its own connection pool.

---

## Sources

- [LangGraph PyPI](https://pypi.org/project/langgraph/) -- v1.0.8 confirmed
- [LangChain Blog: LangChain and LangGraph 1.0](https://blog.langchain.com/langchain-langgraph-1dot0/)
- [langchain-google-genai 4.0.0 Release Discussion](https://github.com/langchain-ai/langchain-google/discussions/1422) -- ChatVertexAI deprecation confirmed
- [Google Gen AI SDK PyPI](https://pypi.org/project/google-genai/) -- v1.62.0
- [Vertex AI Model Versions](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions) -- Gemini 2.5 Flash GA, 3 Flash preview
- [Gemini Embedding Launch](https://developers.googleblog.com/gemini-embedding-available-gemini-api/) -- gemini-embedding-001 GA
- [Supabase pgvector Docs](https://supabase.com/docs/guides/database/extensions/pgvector) -- HNSW indexing, Python integration
- [Perplexity API Pricing](https://docs.perplexity.ai/getting-started/pricing) -- Sonar model tiers, citation token billing change
- [FastAPI PyPI](https://pypi.org/project/fastapi/) -- v0.129.0
- [Pydantic v2.12 Release](https://pydantic.dev/articles/pydantic-v2-12-release) -- v2.12.5
- [langgraph-checkpoint-postgres PyPI](https://pypi.org/project/langgraph-checkpoint-postgres/) -- Postgres checkpointer
- [Google Cloud Blog: Multimodal Agents with Gemini + LangGraph](https://cloud.google.com/blog/products/ai-machine-learning/build-multimodal-agents-using-gemini-langchain-and-langgraph)
- [LangGraph Supervisor vs Swarm Benchmarks](https://blog.langchain.com/benchmarking-multi-agent-architectures/)
- [Develop LangGraph Agent on Vertex AI](https://docs.cloud.google.com/agent-builder/agent-engine/develop/langgraph)
