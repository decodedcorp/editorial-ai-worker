# Feature Landscape

**Domain:** AI-powered fashion editorial content generation (multi-agent pipeline)
**Researched:** 2026-02-20
**Overall confidence:** MEDIUM — Synthesized from multiple web sources, cross-referenced with project context. Fashion editorial AI is a niche intersection; most sources cover general AI content generation or fashion AI separately.

---

## Table Stakes

Features users (admin editors / content managers) expect. Missing = pipeline feels broken or unusable.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| **Trend keyword curation** | Without fresh trending topics, editorial content becomes stale. Every editorial pipeline starts with "what to write about." | Med | Perplexity API, scheduling | Zalando achieved 70% AI-generated editorial content by automating curation. Weekly trigger is minimum cadence. |
| **Structured output (Layout JSON)** | Frontend rendering depends on predictable, schema-validated output. Unstructured text is useless to the rendering pipeline. | High | JSON schema definition, Gemini structured output | This is the contract between AI worker and decoded-app. Schema must be versioned. |
| **Celebrity/influencer search from DB** | Fashion editorials are personality-driven. Content without celebrity context lacks editorial authority. | Med | Supabase celeb table, search/filter logic | Must handle fuzzy matching, relevance ranking. |
| **Product/brand search from DB** | Editorials must reference shoppable products. Without product tie-in, content has no commercial value. | Med | Supabase product/brand tables | Need freshness check — stale/out-of-stock products hurt credibility. |
| **LLM-as-a-Judge quality review** | Without automated quality gate, every piece requires full human review. Defeats the purpose of automation. | High | Review criteria definition, scoring rubrics | Must evaluate: hallucination, format compliance, factual accuracy, editorial tone. Multi-dimension scoring, not binary pass/fail. |
| **Feedback loop (reject + retry)** | Single-shot generation quality is insufficient. Industry standard is evaluate-reflect-refine loop with max retry limit. | High | LangGraph conditional edges, review agent output schema | AWS documents this as "evaluator reflect-refine loop pattern." Must include structured feedback (what failed, why, how to fix). |
| **Human-in-the-loop approval** | Fashion editorial has brand/legal risk. No AI content should auto-publish without human sign-off. | Med | Admin API, status management (pending/approved/rejected) | This is a trust-building feature. Can relax later as confidence grows. |
| **Content preview before publish** | Editors must see what they are approving. Approving a JSON blob is not acceptable. | Med | Frontend rendering of Layout JSON, or embedded preview | Even a simplified preview in admin dashboard suffices for v1. |
| **Execution logging and traceability** | When content is bad, operators need to know which agent failed and why. Essential for debugging multi-agent systems. | Med | LangGraph tracing, structured logs per agent step | OpenAI Agents SDK and LangGraph both emphasize built-in tracing. Non-negotiable for production multi-agent systems. |
| **Retry limits and error handling** | Infinite retry loops waste API credits and block the pipeline. Must fail gracefully. | Low | Config-based max retries, dead letter queue or alert | Simple but critical. Default 3 retries, then escalate to human. |

---

## Differentiators

Features that set this product apart. Not expected by default, but create competitive advantage.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| **Multi-agent orchestration with specialized skills** | Most AI content tools are single-prompt generators. A pipeline with 5 specialized editorial skills (celeb, product, reference, SNS, layout) produces richer, more coherent content than monolithic generation. | High | LangGraph graph definition, tool/skill abstractions | This architecture IS the product differentiator. Each skill can be independently improved. |
| **Source Agent (deep sourcing with Perplexity)** | Fact-grounded editorial content with verifiable URLs. Most AI editorial tools hallucinate sources. | Med | Perplexity API, URL validation | Adds credibility. Source verification separates "AI slop" from "AI-assisted journalism." |
| **SNS content integration** | Embedding real Instagram/YouTube links makes editorials feel current and social-native. Competitors generate text-only content. | Med | SNS API access or URL scraping, embed format support | Legal considerations for embedding. Use oEmbed standards. |
| **External reference collection** | Pulling in reference images and articles from the web gives editorial context that pure generation lacks. | Med | Web scraping/API, image URL validation | Must handle broken links, copyright. Store references as URLs, not copies. |
| **Vector DB similarity search for past content** | Prevents duplicate topics, enables "related articles" linking, and lets the system learn from what worked before. | High | Embedding pipeline, vector DB setup, similarity threshold tuning | Deduplication alone justifies this. Also enables "don't repeat what we published last month." |
| **Multi-dimension review scoring** | Instead of binary pass/fail, scoring across hallucination, tone, format, completeness, product relevance gives granular quality insight. | Med | Review rubric design, per-dimension thresholds | Enables quality analytics over time: "our hallucination rate dropped 40% this month." |
| **Configurable editorial templates** | Different editorial types (celeb spotlight, trend report, product roundup, seasonal lookbook) need different structures. Template-driven generation scales content variety. | Med | Template schema, template selection logic | Start with 2-3 templates. Expand as content types grow. |
| **Feedback-driven prompt refinement** | Using rejection feedback to actually improve the next generation attempt (not just retry with same prompt). The review agent's specific feedback should modify the editorial agent's next attempt. | High | Structured feedback schema, prompt injection from feedback | This is what makes the feedback loop genuinely iterative vs. naive retry. Key differentiator. |
| **Content scheduling and batch generation** | Generate a week's worth of content in one pipeline run, each piece on a different trending topic. | Low | Curation agent returns multiple keywords, pipeline parallelization | Low complexity but high operational value. |
| **Quality analytics dashboard** | Track approval rates, common rejection reasons, quality scores over time. Enables continuous improvement. | Med | Metrics storage, aggregation queries, admin UI charts | Defer charting to post-MVP, but start collecting metrics from day 1. |

---

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Fully autonomous publishing (no human gate)** | Fashion editorial has brand risk, legal risk (celebrity likeness, product claims), and reputational risk. Auto-publishing AI content is how brands get into trouble. | Always require human approval for v1. Can introduce "auto-approve for score > X" later with confidence data. |
| **AI-generated images** | Generated fashion images have uncanny valley problems, copyright ambiguity, and model likeness issues. The domain uses real photography. | Use real product images from DB, real celeb photos from verified sources, reference images via URL. Never generate fake fashion imagery. |
| **Real-time generation on user request** | Editorial content needs review. Real-time generation skips quality control and creates latency expectations the pipeline cannot meet. | Batch generation on schedule (weekly cron). Admin reviews async. Users consume published content. |
| **Complex WYSIWYG editor for admin** | Building a rich editor is a massive frontend effort that distracts from the AI pipeline. The admin's job is approve/reject, not rewrite. | Simple preview + approve/reject/feedback UI. If admin wants to edit, they provide text feedback and the AI regenerates. |
| **Multi-language support in v1** | Doubles prompt engineering effort, review criteria, and testing surface. Korean fashion editorial is the core market. | Build for Korean only. Internationalize the architecture (no hardcoded strings) but defer translation features. |
| **Overly granular admin permissions** | RBAC complexity for a small editorial team is over-engineering. | Single admin role with approve/reject capability. Add roles only when team grows beyond 3-5 people. |
| **Video content generation** | Video AI is a completely different pipeline (diffusion models, rendering, etc.). Mixing it in dilutes focus. | Stick to text + image layout. Support YouTube/Instagram video embeds via URL, not generated video. |
| **Custom LLM fine-tuning** | Fine-tuning is expensive, slow to iterate, and premature before you have enough approved content to form a training set. | Use prompt engineering + few-shot examples + structured output. Revisit fine-tuning after 6+ months of production data. |
| **Plagiarism detection as a separate system** | Building a standalone plagiarism checker is duplicating effort. LLM-as-a-Judge can check for originality as one review dimension. | Include originality/similarity check as a scoring dimension in the review agent. Use vector similarity against past content. |

---

## Feature Dependencies

```
Trend Keyword Curation
  |
  v
Editorial Agent (core generation)
  |--- needs ---> Celeb Search Skill
  |--- needs ---> Product Search Skill
  |--- needs ---> Reference Collection Skill
  |--- needs ---> SNS Content Skill
  |--- produces -> Magazine Layout JSON
  |
  v
Source Agent (fact verification)
  |--- enriches -> Layout JSON with verified URLs
  |
  v
Review Agent (LLM-as-a-Judge)
  |--- pass ----> Admin API (pending status)
  |--- fail ----> Editorial Agent (with structured feedback) [max 3 retries]
  |
  v
Admin Preview + Approve/Reject
  |--- approve -> Publish Pipeline
  |--- reject --> Editorial Agent (with human feedback) OR discard
  |
  v
Published Content (Supabase)

Cross-cutting dependencies:
- Vector DB <--- needed by ---> Curation (dedup), Editorial (past content reference)
- Supabase <--- needed by ---> Celeb Search, Product Search, Admin API, Published Content
- Layout JSON Schema <--- needed by ---> Editorial Agent, Review Agent (format check), Admin Preview, Frontend
- Tracing/Logging <--- needed by ---> All agents (debugging, analytics)
```

---

## MVP Recommendation

For MVP, prioritize in this order:

### Must ship (Table Stakes)
1. **Trend keyword curation** via Perplexity — the pipeline's input
2. **Editorial Agent with 3 core skills** — celeb search, product search, layout JSON output
3. **LLM-as-a-Judge review** with structured feedback
4. **Feedback loop** with max retry (3 attempts)
5. **Admin API** — save to Supabase with pending/approved/rejected status
6. **Simple admin preview + approve/reject UI**
7. **Execution tracing** per pipeline run

### Include in MVP (high-value differentiators, low marginal cost)
8. **Source Agent** — adds credibility, relatively simple with Perplexity
9. **Structured feedback in retry** — makes feedback loop actually useful vs. naive retry
10. **Content scheduling** (weekly cron) — operational necessity

### Defer to post-MVP
- **Vector DB similarity search** — valuable but adds infra complexity. Use simple keyword dedup initially.
- **SNS content integration** — nice to have, API access can be complex.
- **External reference collection** — web scraping is fragile. Manual reference URLs in v1.
- **Configurable editorial templates** — start with one template, add more based on content needs.
- **Quality analytics dashboard** — collect metrics from day 1, build visualization later.
- **Multi-dimension review scoring breakdown** — start with overall pass/fail + text feedback. Add granular dimensions in v2.

---

## Sources

- [AI Content Generation Tools Guide 2026 — Infozzle](https://www.infozzle.com/blog/ai-content-generation-tools-the-2026-guide-to-faster-higher-ranking-content/) — General AI content platform features landscape
- [AI Fashion Trends 2026 — Fashion Diffusion](https://www.fashiondiffusion.ai/blog/ai-fashion-trends-2026) — Fashion-specific AI capabilities
- [Top 11 AI in Fashion Use Cases 2026 — AIMultiple](https://research.aimultiple.com/ai-in-fashion/) — Fashion AI use cases including editorial
- [LLM-as-a-Judge Complete Guide — Evidently AI](https://www.evidentlyai.com/llm-guide/llm-as-a-judge) — LLM evaluation patterns and best practices
- [LLM-as-Judge Best Practices — Monte Carlo Data](https://www.montecarlodata.com/blog-llm-as-judge/) — Multi-dimension evaluation templates
- [Evaluator Reflect-Refine Loop Patterns — AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/evaluator-reflect-refine-loop-patterns.html) — Feedback loop architecture patterns
- [The 2026 Guide to AI Agent Workflows — Vellum](https://www.vellum.ai/blog/agentic-workflows-emerging-architectures-and-design-patterns) — Multi-agent orchestration patterns
- [AI Agents vs AI Workflows — IntuitionLabs](https://intuitionlabs.ai/articles/ai-agent-vs-ai-workflow) — Pipeline vs agent architecture tradeoffs
- [AI Fashion Recommendation Systems — Springer](https://link.springer.com/article/10.1007/s42979-023-01932-9) — Celebrity fashion content curation patterns
- [AI and Fashion E-Commerce Content — BoF](https://www.businessoffashion.com/articles/technology/bof-voices-ai-and-the-future-of-fashion-ecommerce-content/) — Fashion editorial automation (Zalando case)
