"""Prompt templates for the editorial content generation pipeline.

Five prompt builders for the 3-step editorial pipeline:
1. build_content_generation_prompt — Gemini structured output for editorial content
2. build_content_generation_prompt_with_feedback — Feedback-aware variant for retry iterations
3. build_layout_image_prompt — Nano Banana image generation for layout design
4. build_layout_parsing_prompt — Vision AI to parse layout image into block JSON
5. build_output_repair_prompt — Fix malformed JSON using Gemini
"""


def build_content_generation_prompt(keyword: str, trend_context: str) -> str:
    """Build prompt for Gemini structured output to generate editorial content.

    Instructs Gemini to produce a Korean fashion editorial article (~500 chars)
    that matches the EditorialContent schema.
    """
    return f"""당신은 패션 매거진 에디터입니다.
세련되고, 정보가 풍부하며, 읽는 재미가 있는 에디토리얼 콘텐츠를 작성합니다.

다음 키워드와 트렌드 배경을 바탕으로 패션 에디토리얼 콘텐츠를 작성해주세요.

키워드: {keyword}

트렌드 배경:
{trend_context}

작성 조건:
- title: 매력적인 에디토리얼 제목 (한국어)
- subtitle: 부제목 (한국어, 1문장)
- body_paragraphs: 본문 2~3개 단락 (각 150~250자, 한국어)
- pull_quotes: 인상적인 인용문 1~2개 (본문에서 발췌하거나 새로 작성)
- product_mentions: 관련 상품/브랜드 언급 (name, brand, context 포함).
  실제 패션 브랜드와 제품을 언급하세요.
- celeb_mentions: 관련 셀럽/인플루언서 언급 (name, context 포함). 실제 인물을 언급하세요.
- hashtags: 관련 해시태그 3~5개 (# 없이 텍스트만)
- credits: 크레딧 정보 (role, name). 최소 1개 (예: AI Editor / decoded editorial)
- keyword: "{keyword}"

톤: 패션 매거진 에디터 톤 - 세련되고, 트렌디하며, 독자의 흥미를 끄는 문체
언어: 한국어 (영어 고유명사는 영어 그대로 사용 가능)

반드시 유효한 JSON만 출력하세요. 마크다운 코드 펜스나 추가 설명을 포함하지 마세요."""


def build_content_generation_prompt_with_feedback(
    keyword: str,
    trend_context: str,
    feedback_history: list[dict],
    previous_draft: dict | None = None,
) -> str:
    """Build editorial prompt with injected review feedback for retry iterations.

    Feedback is placed BEFORE the main generation instructions so the LLM
    prioritizes addressing prior failures.
    """
    feedback_section = "--- 이전 검수 피드백 (반드시 반영하세요) ---\n\n"

    for i, feedback in enumerate(feedback_history, 1):
        feedback_section += f"[시도 {i}]\n"
        for criterion in feedback.get("criteria", []):
            if not criterion.get("passed"):
                feedback_section += (
                    f"- {criterion['criterion']}: {criterion['reason']}\n"
                )
        suggestions = feedback.get("suggestions", [])
        if suggestions:
            feedback_section += f"개선 제안: {', '.join(suggestions)}\n"
        feedback_section += "\n"

    if previous_draft:
        prev_title = previous_draft.get("title", "N/A")
        feedback_section += f"이전 초안 제목: {prev_title}\n"
        feedback_section += "위 피드백을 반영하여 완전히 새로운 초안을 작성하세요.\n\n"

    # Feedback BEFORE main prompt for maximum LLM attention
    base_prompt = build_content_generation_prompt(keyword, trend_context)
    return feedback_section + base_prompt


def build_layout_image_prompt(keyword: str, title: str, num_sections: int) -> str:
    """Build prompt for Nano Banana to generate a magazine layout design image.

    This prompt generates an IMAGE (not text). The output image will be parsed
    by Vision AI in the next step.
    """
    return f"""Create a clean, minimalist fashion magazine layout design for an editorial article.

Theme: {keyword}
Title: {title}
Number of content sections: {num_sections}

Design requirements:
- Modern fashion magazine aesthetic (think Vogue, Harper's Bazaar, Elle)
- Clean grid layout with clear section boundaries
- Include these section areas:
  1. Large hero image area at the top (full-width)
  2. Headline/title typography area
  3. Body text columns ({num_sections - 4 if num_sections > 4 else 1} text section(s))
  4. Product showcase area (grid of product cards)
  5. Celebrity feature area
  6. Hashtag bar at the bottom
- Use placeholder rectangles for images (labeled "IMAGE")
- Use horizontal lines for text areas (labeled "TEXT")
- Minimalist color palette: white background, black text areas, light gray image placeholders
- Portrait orientation (9:16 aspect ratio)
- No actual text content, only layout wireframe with labeled areas
- Each section should be clearly separated with whitespace or thin dividers"""


def build_layout_parsing_prompt(keyword: str, block_types: list[str]) -> str:
    """Build prompt for Vision AI to parse a layout image into block structure JSON.

    Instructs Gemini Vision to analyze the magazine layout image and extract
    an ordered list of block definitions.
    """
    block_types_str = ", ".join(f'"{bt}"' for bt in block_types)
    return f"""이 매거진 레이아웃 디자인 이미지를 분석하여, 블록 구조를 JSON으로 추출해주세요.

키워드: {keyword}

사용 가능한 블록 타입: [{block_types_str}]

이미지에서 보이는 레이아웃 섹션을 위에서 아래로 순서대로 분석하여,
각 섹션에 맞는 블록 타입을 지정해주세요.

출력 형식 (JSON 배열):
[
  {{"type": "hero", "order": 0}},
  {{"type": "headline", "order": 1}},
  {{"type": "body_text", "order": 2}},
  ...
]

규칙:
- order는 0부터 시작하는 순서 번호
- type은 위의 사용 가능한 블록 타입 중 하나
- 이미지에서 식별할 수 없는 섹션은 건너뛰세요
- 최소 3개, 최대 12개의 블록을 출력하세요

반드시 유효한 JSON 배열만 출력하세요."""


def build_output_repair_prompt(model_name: str, raw_json: str, error_message: str) -> str:
    """Build prompt to fix malformed JSON that failed Pydantic validation.

    Sends the broken JSON and validation error to Gemini for correction.
    """
    return f"""다음 JSON이 {model_name} 스키마 검증에 실패했습니다.
검증 오류만 수정하고 콘텐츠는 변경하지 마세요.

원본 JSON:
{raw_json}

검증 오류:
{error_message}

수정 조건:
- 검증 오류에서 지적된 문제만 수정
- 기존 콘텐츠(텍스트, 값 등)는 최대한 유지
- 누락된 필수 필드는 합리적인 기본값으로 채움
- 잘못된 타입은 올바른 타입으로 변환

반드시 수정된 유효한 JSON만 출력하세요. 마크다운 코드 펜스나 추가 설명을 포함하지 마세요."""
