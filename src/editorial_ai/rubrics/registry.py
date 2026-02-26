"""Adaptive rubric registry -- content-type-specific evaluation criteria.

Maps ContentType to RubricConfig with weighted criteria and prompt additions
for the review LLM-as-a-Judge evaluation.
"""

from dataclasses import dataclass, field
from enum import Enum


class ContentType(str, Enum):
    FASHION_MAGAZINE = "fashion_magazine"
    TECH_BLOG = "tech_blog"
    LIFESTYLE = "lifestyle"
    DEFAULT = "default"


@dataclass
class RubricCriterion:
    """A single evaluation criterion with weight."""

    name: str
    weight: float  # 0.0 to 1.5 -- higher = stricter scoring
    description: str  # Injected into review prompt


@dataclass
class RubricConfig:
    """Content-type-specific evaluation configuration."""

    content_type: ContentType
    criteria: list[RubricCriterion]
    prompt_additions: str  # Extra review instructions for this content type


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

RUBRIC_REGISTRY: dict[ContentType, RubricConfig] = {
    ContentType.FASHION_MAGAZINE: RubricConfig(
        content_type=ContentType.FASHION_MAGAZINE,
        criteria=[
            RubricCriterion(
                name="hallucination",
                weight=1.0,
                description="큐레이션 데이터에 없는 허위 브랜드명, 존재하지 않는 셀럽, 날조된 이벤트/컬렉션 검출.",
            ),
            RubricCriterion(
                name="fact_accuracy",
                weight=1.0,
                description="브랜드명, 셀럽명, 트렌드 설명이 큐레이션 데이터와 일치하는지 확인.",
            ),
            RubricCriterion(
                name="content_completeness",
                weight=1.0,
                description="셀럽/인플루언서, 상품/브랜드, 본문 단락, 해시태그 등 필수 구성요소 포함 여부.",
            ),
            RubricCriterion(
                name="visual_appeal",
                weight=0.8,
                description="시각적 표현력 -- 패션 이미지와 스타일링 묘사가 생생하고 매거진에 적합한지 평가. 추상적이거나 밋밋한 표현은 감점.",
            ),
            RubricCriterion(
                name="trend_relevance",
                weight=0.9,
                description="트렌드 반영도 -- 최신 패션 트렌드, 시즌 키워드, 런웨이 레퍼런스가 정확하게 반영되었는지 평가.",
            ),
        ],
        prompt_additions=(
            "패션 에디토리얼로서의 매력과 트렌드 정확성을 중점 평가하세요. "
            "시각적 묘사의 풍부함과 브랜드/셀럽 언급의 자연스러움에 주목하세요."
        ),
    ),
    ContentType.TECH_BLOG: RubricConfig(
        content_type=ContentType.TECH_BLOG,
        criteria=[
            RubricCriterion(
                name="hallucination",
                weight=1.0,
                description="큐레이션 데이터에 없는 허위 정보, 존재하지 않는 기술/제품, 날조된 사실 검출.",
            ),
            RubricCriterion(
                name="fact_accuracy",
                weight=1.2,
                description="기술 용어, 제품명, 버전 정보, 기술 개념 설명이 정확한지 확인. 기술 콘텐츠는 정확성이 특히 중요.",
            ),
            RubricCriterion(
                name="content_completeness",
                weight=1.0,
                description="핵심 기술 개념, 실용 예시, 결론 등 필수 구성요소 포함 여부.",
            ),
            RubricCriterion(
                name="technical_depth",
                weight=0.9,
                description="기술적 깊이 -- 기술 개념의 설명이 충분한 깊이를 가지며, 표면적 나열이 아닌 실질적 분석을 포함하는지 평가.",
            ),
        ],
        prompt_additions=(
            "기술 블로그로서 용어의 정확성, 개념 설명의 깊이, 실용적 인사이트를 중점 평가하세요."
        ),
    ),
    ContentType.LIFESTYLE: RubricConfig(
        content_type=ContentType.LIFESTYLE,
        criteria=[
            RubricCriterion(
                name="hallucination",
                weight=1.0,
                description="큐레이션 데이터에 없는 허위 정보, 날조된 장소/이벤트 검출.",
            ),
            RubricCriterion(
                name="fact_accuracy",
                weight=0.8,
                description="언급된 장소, 브랜드, 트렌드 정보의 정확성 확인. 라이프스타일은 다소 유연하게 평가.",
            ),
            RubricCriterion(
                name="content_completeness",
                weight=1.0,
                description="핵심 주제, 실용적 팁, 영감 요소 등 필수 구성요소 포함 여부.",
            ),
            RubricCriterion(
                name="engagement",
                weight=0.8,
                description="독자 공감도 -- 라이프스타일 콘텐츠로서 독자의 일상과 연결되는 공감 요소가 있는지, 실용적 팁이나 영감을 주는지 평가.",
            ),
        ],
        prompt_additions=(
            "라이프스타일 콘텐츠로서 독자 공감과 실용성을 중점 평가하세요."
        ),
    ),
}

# DEFAULT = same as FASHION_MAGAZINE (this pipeline is fashion-first)
RUBRIC_REGISTRY[ContentType.DEFAULT] = RubricConfig(
    content_type=ContentType.DEFAULT,
    criteria=RUBRIC_REGISTRY[ContentType.FASHION_MAGAZINE].criteria,
    prompt_additions=RUBRIC_REGISTRY[ContentType.FASHION_MAGAZINE].prompt_additions,
)


def get_rubric(content_type: ContentType) -> RubricConfig:
    """Get rubric config for a content type, falling back to DEFAULT."""
    return RUBRIC_REGISTRY.get(content_type, RUBRIC_REGISTRY[ContentType.DEFAULT])
