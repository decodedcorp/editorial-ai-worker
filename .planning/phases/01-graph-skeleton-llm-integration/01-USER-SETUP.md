# Phase 1 User Setup

Status: **Incomplete**

## Environment Variables

The following environment variables must be configured before proceeding with Plan 01-02.

| Variable | Required | Source | Purpose |
|----------|----------|--------|---------|
| `GOOGLE_API_KEY` | Yes (for local dev) | [Google AI Studio](https://aistudio.google.com/apikey) -> Create API Key | Gemini LLM calls (Developer API free tier) |
| `LANGSMITH_API_KEY` | Yes | [LangSmith](https://smith.langchain.com) -> Settings -> API Keys -> Create | LLM tracing and observability |

## Setup Steps

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Get your Google API Key:
   - Go to https://aistudio.google.com/apikey
   - Click "Create API Key"
   - Copy the key into `.env` as `GOOGLE_API_KEY=<your-key>`

3. Get your LangSmith API Key:
   - Go to https://smith.langchain.com
   - Navigate to Settings -> API Keys -> Create
   - Copy the key into `.env` as `LANGSMITH_API_KEY=<your-key>`

## Verification

After setting up environment variables, run:

```bash
# Verify config loads correctly
uv run python -c "
from editorial_ai.config import settings
assert settings.google_api_key is not None, 'GOOGLE_API_KEY not set'
assert settings.langsmith_api_key is not None, 'LANGSMITH_API_KEY not set'
print(f'Google API Key: ...{settings.google_api_key[-4:]}')
print(f'LangSmith Key: ...{settings.langsmith_api_key[-4:]}')
print('All keys configured!')
"
```
