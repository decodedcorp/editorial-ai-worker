"""Keyword-based content type classifier.

Simple rule-based classification from seed keyword and curated topic keywords.
No ML -- just keyword domain matching. Default is FASHION_MAGAZINE.
"""

from editorial_ai.rubrics.registry import ContentType

# Keyword -> ContentType mapping (lowercase keys)
KEYWORD_DOMAIN_MAP: dict[str, ContentType] = {}

_TECH_KEYWORDS = [
    "ai", "tech", "developer", "coding", "programming", "software",
    "startup", "saas", "cloud", "api", "machine learning", "deep learning",
    "blockchain",
]

_FASHION_KEYWORDS = [
    "fashion", "style", "trend", "runway", "couture", "streetwear",
    "vogue", "lookbook", "outfit", "styling",
]

_LIFESTYLE_KEYWORDS = [
    "wellness", "travel", "home decor", "food", "fitness",
    "mindfulness", "interior", "recipe",
]

for _kw in _TECH_KEYWORDS:
    KEYWORD_DOMAIN_MAP[_kw] = ContentType.TECH_BLOG
for _kw in _FASHION_KEYWORDS:
    KEYWORD_DOMAIN_MAP[_kw] = ContentType.FASHION_MAGAZINE
for _kw in _LIFESTYLE_KEYWORDS:
    KEYWORD_DOMAIN_MAP[_kw] = ContentType.LIFESTYLE

# Sort by keyword length descending so longer (more specific) matches win.
# E.g. "home decor" matches before "trend" in "home decor trends".
_SORTED_KEYWORDS = sorted(KEYWORD_DOMAIN_MAP.items(), key=lambda x: len(x[0]), reverse=True)


def classify_content_type(
    keyword: str,
    curated_topics: list[dict] | None = None,
) -> ContentType:
    """Classify content type from seed keyword and optional curated topics.

    Strategy:
    1. Check seed keyword for domain substring matches
    2. Check curated_topics related_keywords if provided
    3. Default to FASHION_MAGAZINE (fashion-first pipeline)
    """
    normalized = keyword.lower()

    # Check seed keyword against domain keywords (longest match first)
    for domain_kw, content_type in _SORTED_KEYWORDS:
        if domain_kw in normalized:
            return content_type

    # Check curated topics related_keywords
    if curated_topics:
        for topic in curated_topics:
            related = topic.get("related_keywords", [])
            for rk in related:
                rk_lower = rk.lower() if isinstance(rk, str) else ""
                for domain_kw, content_type in _SORTED_KEYWORDS:
                    if domain_kw in rk_lower:
                        return content_type

    # Default: fashion-first pipeline
    return ContentType.FASHION_MAGAZINE
