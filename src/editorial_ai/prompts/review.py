"""Prompt template for the review agent LLM-as-a-Judge evaluation.

Single prompt builder for semantic evaluation of editorial drafts.
Format validation is handled deterministically by Pydantic -- NOT by the LLM.
"""


def build_review_prompt(draft_json: str, curated_topics_json: str) -> str:
    """Build prompt for LLM-as-a-Judge evaluation of an editorial draft.

    The prompt instructs Gemini to evaluate 3 semantic criteria:
    - hallucination: fabricated info not in curated data
    - fact_accuracy: brand/celeb/trend names match curated data
    - content_completeness: structural requirements met

    Format validation is NOT included -- handled by Pydantic separately.

    Args:
        draft_json: The full MagazineLayout JSON to evaluate.
        curated_topics_json: The curated topics JSON as ground truth for fact-checking.

    Returns:
        Prompt string for Gemini structured output.
    """
    return f"""당신은 패션 매거진 편집장으로서 에디토리얼 초안을 검수합니다.
아래의 에디토리얼 초안(Draft)을 큐레이션 데이터(Ground Truth)와 대조하여 평가해주세요.

## 에디토리얼 초안 (Draft)
{draft_json}

## 큐레이션 데이터 (Ground Truth)
{curated_topics_json}

## 평가 기준

다음 3가지 기준으로 평가하세요:

### 1. hallucination (환각 검출)
- 큐레이션 데이터에 없는 **허위** 브랜드명, 존재하지 않는 셀럽, 날조된 이벤트/컬렉션이 있는지 확인
- 큐레이션 데이터를 기반으로 한 자연스러운 문맥 보충, 일반 상식 수준의 부연 설명은 환각이 아님
- 환각으로 간주하는 경우: 실존하지 않는 고유명사(브랜드/셀럽/장소), 날조된 수치/날짜/이벤트
- severity: critical (날조된 고유명사 또는 허위 사실), minor (경미한 표현 차이나 과장)

### 2. fact_accuracy (사실 정확성)
- 브랜드명, 셀럽명, 트렌드 설명이 큐레이션 데이터와 일치하는지 확인
- 이름 오타, 잘못된 브랜드-제품 연결, 부정확한 트렌드 설명 검출
- severity: critical (이름 오류), major (설명 부정확)

### 3. content_completeness (콘텐츠 완성도)
- 셀럽/인플루언서 참조 1개 이상 포함 여부
- 상품/브랜드 참조 1개 이상 포함 여부
- 본문 2개 이상 단락 포함 여부
- 해시태그 포함 여부
- severity: major (핵심 요소 누락), minor (부가 요소 누락)

## 출력 형식

각 기준에 대해 다음을 출력하세요:
- criterion: 기준 이름 (hallucination, fact_accuracy, content_completeness)
- passed: true/false
- reason: 구체적이고 실행 가능한 설명 (한국어)
- severity: critical, major, minor

전체 결과:
- passed: 모든 기준이 통과하면 true, 하나라도 실패하면 false
- criteria: 위 3개 기준 결과 배열
- summary: 전체 평가 요약 (1-2문장, 한국어)
- suggestions: 개선 제안 목록 (실패한 기준에 대해)

반드시 유효한 JSON만 출력하세요."""
