"""Prompt templates for the curation pipeline.

Three prompt builders for the two-step Gemini grounding pattern:
1. build_trend_research_prompt — grounded search call
2. build_subtopic_expansion_prompt — extract sub-topic keywords
3. build_extraction_prompt — structured JSON extraction from research text
"""


def build_trend_research_prompt(keyword: str, *, db_context: str = "") -> str:
    """Build prompt for grounded Gemini research call.

    Instructs the model to use Google Search grounding to research current
    fashion trends related to the keyword, anchored to available DB data.
    """
    db_section = ""
    if db_context:
        db_section = f"""

--- 우리 데이터베이스에 보유한 콘텐츠 ---
{db_context}

중요: 위 아티스트와 브랜드는 우리 DB에 실제 이미지와 상품 데이터가 있습니다.
트렌드를 조사할 때 이 아티스트들과 브랜드를 중심으로 리서치하세요.
키워드와 관련된 이 아티스트들의 최신 패션 활동, 착용 아이템, 스타일링을 조사하세요.
"""

    return f"""당신은 패션 에디토리얼 전문 리서처입니다.
다음 키워드에 대해 최신 패션 트렌드를 종합적으로 조사해주세요.

키워드: {keyword}
{db_section}
다음 항목을 포함하여 상세하게 작성해주세요:

1. **트렌드 배경 (Trend Background)**: 이 트렌드가 왜 주목받고 있는지, 패션 업계에서의 맥락
2. **관련 키워드 (Related Keywords)**: 이 트렌드와 연관된 패션 키워드 5-10개. 반드시 아티스트 이름(예: jennie, hanni, minji 등)을 2-3개 포함하세요.
3. **관련 셀럽/인플루언서 (Celebrities)**: 이 트렌드를 리드하거나 착용한 셀럽들과 각각의 관련성
4. **관련 브랜드/제품 (Brands & Products)**: 이 트렌드와 관련된 브랜드나 제품들과 각각의 관련성
5. **시즌성 (Seasonality)**: 이 트렌드의 시즌 특성 (예: S/S 2025, year-round, transitional 등)

Google Search를 활용하여 최신 정보를 반영해주세요.
한국어와 영어를 혼용하여 작성해도 됩니다.
가능한 한 구체적이고 최신 정보를 포함해주세요."""


def build_subtopic_expansion_prompt(keyword: str, trend_background: str) -> str:
    """Build prompt to extract sub-topic keywords from initial research.

    Returns a prompt that asks for a JSON array of 3-7 sub-topic keyword strings.
    """
    return f"""다음 패션 트렌드 리서치를 바탕으로, 에디토리얼 콘텐츠로 확장할 수 있는 \
세부 주제(sub-topic) 키워드를 추출해주세요.

메인 키워드: {keyword}

리서치 내용:
{trend_background}

조건:
- 3~7개의 세부 키워드를 JSON 배열로 반환
- 각 키워드는 메인 키워드의 세부 측면이나 관련 트렌드
- 에디토리얼 콘텐츠로 발전시킬 수 있는 구체적인 키워드
- 메인 키워드 자체는 포함하지 마세요

반드시 JSON 배열만 출력하세요. 예시:
["키워드1", "키워드2", "키워드3"]"""


def build_extraction_prompt(keyword: str, raw_research: str) -> str:
    """Build prompt for structured JSON extraction from grounded research text.

    Instructs the model to output ONLY valid JSON matching the CuratedTopic schema.
    """
    return f"""다음 패션 트렌드 리서치 텍스트를 분석하여, 구조화된 JSON으로 변환해주세요.

키워드: {keyword}

리서치 텍스트:
{raw_research}

다음 JSON 스키마에 맞춰 출력하세요. 반드시 유효한 JSON만 출력하세요:

{{
  "keyword": "{keyword}",
  "trend_background": "트렌드 배경 요약 (2-3문장)",
  "related_keywords": ["관련 키워드1", "관련 키워드2", ...],
  "celebrities": [
    {{"name": "셀럽 이름", "relevance": "관련성 설명"}},
    ...
  ],
  "brands_products": [
    {{"name": "브랜드/제품명", "relevance": "관련성 설명"}},
    ...
  ],
  "seasonality": "시즌 특성 (예: S/S 2025, year-round)",
  "relevance_score": 0.0~1.0 사이의 트렌드 관련성 점수
}}

점수 기준:
- 0.9-1.0: 현재 매우 핫한 트렌드, 다수 매체 보도
- 0.7-0.8: 주목할 만한 트렌드, 일부 매체/셀럽 관련
- 0.5-0.6: 관련성 있으나 아직 초기 단계
- 0.3-0.4: 간접적으로만 관련

반드시 위 JSON 형식만 출력하세요. 추가 설명이나 마크다운은 포함하지 마세요."""
