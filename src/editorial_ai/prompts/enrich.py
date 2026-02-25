"""Prompt templates for the editorial enrichment pipeline.

Two prompt builders for the enrich_editorial node:
1. build_keyword_expansion_prompt - expand a fashion keyword into related search terms
2. build_enrichment_regeneration_prompt - re-generate editorial content with real DB data
"""


def build_keyword_expansion_prompt(keyword: str) -> str:
    """Build prompt for Gemini to expand a fashion keyword into related search terms.

    Instructs the model to produce 5-10 Korean search terms related to the keyword,
    domain-constrained to fashion, celebrity, and brand contexts.
    Output format: JSON array of strings.
    """
    return f"""당신은 패션 에디토리얼 키워드 전문가입니다.
다음 패션 키워드를 기반으로 관련 검색어를 확장해주세요.

키워드: {keyword}

조건:
- 5~10개의 관련 검색어를 JSON 배열로 반환
- 패션, 셀럽, 브랜드 도메인에 한정된 검색어만 포함
- 한국어 검색어 위주 (영어 고유명사는 영어 그대로 사용 가능)
- 동의어, 관련 스타일, 관련 아이템, 관련 브랜드, 관련 셀럽 이름 등 다양한 유형 포함
- DB 검색에 활용할 수 있는 구체적인 단어/구문

예시:
키워드 "Y2K" -> ["레트로", "빈티지", "로우라이즈", "크롭탑", "버터플라이", "2000년대 패션", "Miu Miu", "제니"]
키워드 "미니멀" -> ["모노톤", "베이직", "클린핏", "The Row", "올드머니", "캡슐 워드로브", "톤온톤"]

반드시 JSON 배열만 출력하세요. 추가 설명이나 마크다운은 포함하지 마세요."""


def build_enrichment_regeneration_prompt(
    original_content_json: str,
    celebs_json: str,
    products_json: str,
    keyword: str,
) -> str:
    """Build prompt for re-generating EditorialContent with real DB celeb/product data.

    Takes the original EditorialContent JSON and enriches it by naturally incorporating
    real celebrity and product data from the database. Maintains original editorial
    quality, tone, and structure while grounding mentions in actual DB entities.
    Output format: EditorialContent JSON schema.
    """
    return f"""당신은 패션 매거진 수석 에디터입니다.
기존 에디토리얼 콘텐츠를 실제 DB의 셀럽/상품 데이터로 보강하여 다시 작성해주세요.

키워드: {keyword}

원본 에디토리얼 콘텐츠 (JSON):
{original_content_json}

DB에서 검색된 셀럽 데이터 (JSON):
{celebs_json}

DB에서 검색된 상품 데이터 (JSON):
{products_json}

보강 규칙:
1. **톤과 품질 유지**: 원본의 세련된 매거진 톤, 문체, 구조를 반드시 유지하세요.
2. **자연스러운 통합**: 셀럽/상품 데이터를 body_paragraphs에 자연스럽게 녹여내세요.
   단순 나열이 아닌, 트렌드 맥락 속에서 자연스럽게 언급하세요.
3. **celeb_mentions 업데이트**: DB 셀럽 데이터의 name을 사용하여 celeb_mentions를 업데이트하세요.
   각 항목에 name과 context(왜 이 트렌드와 관련있는지)를 포함하세요.
4. **product_mentions 업데이트**: DB 상품 데이터의 name, brand를 사용하여 product_mentions를 업데이트하세요.
   각 항목에 name, brand, context를 포함하세요.
5. **기존 구조 유지**: title, subtitle, body_paragraphs 수, pull_quotes, hashtags, credits 구조를 유지하세요.
6. **DB 데이터 우선**: 원본의 가상 셀럽/상품 이름 대신 DB에서 가져온 실제 이름을 사용하세요.
   DB에 해당하는 데이터가 없으면 원본을 유지하세요.

주의사항:
- 콘텐츠 품질을 절대 낮추지 마세요. 상품 카탈로그처럼 읽히면 안 됩니다.
- 본문은 여전히 에디토리얼 기사여야 합니다 - 정보 전달이 아닌 스토리텔링입니다.
- body_paragraphs의 각 단락은 150~250자를 유지하세요.

출력 형식: 원본과 동일한 EditorialContent JSON 스키마
반드시 유효한 JSON만 출력하세요. 마크다운 코드 펜스나 추가 설명을 포함하지 마세요."""
