"""Test Gemini with Google Search Grounding for fashion trend curation.

Usage:
    uv run python scripts/test_grounding.py "Y2K"
    uv run python scripts/test_grounding.py "리넨 패션"
"""

import os
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(".env")
load_dotenv(".env.local", override=True)

# Explicitly use Developer API (API key), not Vertex AI
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


def curate_trend(keyword: str) -> None:
    """Test trend curation with Google Search Grounding."""

    prompt = f"""당신은 패션 에디토리얼 큐레이터입니다.

키워드: "{keyword}"

이 키워드에 대해 다음 정보를 수집해주세요:

1. **트렌드 배경**: 이 트렌드가 왜 주목받고 있는지 (3-5문장)
2. **연관 키워드**: 에디토리얼 작성에 활용할 수 있는 연관 키워드 5-10개
3. **관련 셀럽/인플루언서**: 이 트렌드와 관련된 유명인 3-5명 (이름, 관련성)
4. **관련 브랜드/상품**: 이 트렌드를 대표하는 브랜드나 상품 3-5개
5. **시즌/시기**: 이 트렌드의 시즌성 또는 시기적 관련성

JSON 형식으로 응답해주세요:
{{
    "keyword": "{keyword}",
    "trend_background": "...",
    "related_keywords": ["...", "..."],
    "celebrities": [
        {{"name": "...", "relevance": "..."}}
    ],
    "brands_products": [
        {{"name": "...", "relevance": "..."}}
    ],
    "seasonality": "..."
}}
"""

    print(f"\n{'='*60}")
    print(f"Testing keyword: {keyword}")
    print(f"{'='*60}\n")

    # With Google Search Grounding
    print("--- With Google Search Grounding ---\n")
    response_grounded = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.7,
        ),
    )
    print(response_grounded.text)

    # Show grounding metadata
    if response_grounded.candidates and response_grounded.candidates[0].grounding_metadata:
        metadata = response_grounded.candidates[0].grounding_metadata
        print("\n--- Grounding Sources ---")
        if metadata.grounding_chunks:
            for i, chunk in enumerate(metadata.grounding_chunks):
                if chunk.web:
                    print(f"  [{i+1}] {chunk.web.title}")
                    print(f"      {chunk.web.uri}")
        print(f"\n  Total sources: {len(metadata.grounding_chunks or [])}")

    print(f"\n{'='*60}")

    # Without grounding (for comparison)
    print("\n--- Without Grounding (comparison) ---\n")
    response_plain = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
        ),
    )
    print(response_plain.text)


if __name__ == "__main__":
    keyword = sys.argv[1] if len(sys.argv) > 1 else "Y2K 패션"
    curate_trend(keyword)
