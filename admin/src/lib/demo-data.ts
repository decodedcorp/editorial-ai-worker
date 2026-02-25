/**
 * Demo mock data for UI verification without a live backend.
 * Activate with DEMO_MODE=true in .env.local.
 *
 * Data mirrors the editorial_contents table schema and references
 * realistic Korean fashion editorial content with celeb/product structures
 * matching the production Supabase celebs/products tables.
 */

import type { ContentItem } from "./types";

// ---------------------------------------------------------------------------
// In-memory store (mutations persist for session lifetime)
// ---------------------------------------------------------------------------

const demoItems: ContentItem[] = [
  {
    id: "demo-001",
    thread_id: "thread-demo-001",
    status: "pending",
    title: "2026 S/S 뉴진스가 선택한 데님 트렌드",
    keyword: "뉴진스 데님",
    layout_json: {
      schema_version: "1.0",
      title: "2026 S/S 뉴진스가 선택한 데님 트렌드",
      subtitle: "올 봄, 가장 핫한 데님 스타일링의 모든 것",
      keyword: "뉴진스 데님",
      blocks: [
        { type: "hero", image_url: "https://placeholder.co/1200x675", overlay_title: "Denim Revolution", overlay_subtitle: "2026 S/S Collection" },
        { type: "headline", text: "뉴진스가 이끄는 2026 데님 혁명", level: 1 },
        { type: "body_text", paragraphs: [
          "올 시즌 데님은 단순한 캐주얼을 넘어 하이패션의 영역으로 진입했다. 특히 뉴진스 멤버들이 공항패션과 화보에서 선보인 와이드 데님 룩은 글로벌 트렌드로 자리잡았다.",
          "Louis Vuitton의 2026 S/S 컬렉션에서 영감을 받은 오버사이즈 데님 재킷부터, Acne Studios의 미니멀한 로우라이즈 진까지 — 데님의 스펙트럼은 그 어느 때보다 넓어졌다.",
          "핵심은 '믹스 매치'다. 데님 온 데님 룩에 실크 블라우스를 더하거나, 테일러드 블레이저 아래 빈티지 워싱 진을 매치하는 것이 이번 시즌의 키 스타일링이다."
        ] },
        { type: "celeb_feature", celebs: [
          { celeb_id: "celeb-001", name: "민지", image_url: null, description: "루이비통 글로벌 앰배서더. 공항패션에서 와이드 데님 + 크롭탑 조합으로 화제" },
          { celeb_id: "celeb-002", name: "하니", image_url: null, description: "구찌 앰배서더. 빈티지 워싱 데님 재킷을 시그니처 아이템으로 활용" }
        ] },
        { type: "image_gallery", images: [
          { url: "https://placeholder.co/600x600", alt: "와이드 데님 룩", caption: "뉴진스 민지의 공항패션 (2026.02)" },
          { url: "https://placeholder.co/600x600", alt: "데님 온 데님", caption: "하니의 데님 레이어링" },
          { url: "https://placeholder.co/600x600", alt: "로우라이즈 데님", caption: "Acne Studios S/S 2026" }
        ], layout_style: "grid" },
        { type: "pull_quote", quote: "데님은 세대를 초월하는 유일한 패브릭이다. 올해의 데님은 자유와 자기표현을 상징한다.", attribution: "Nicolas Ghesquière, Louis Vuitton Creative Director" },
        { type: "product_showcase", products: [
          { product_id: "prod-001", name: "Wide Leg Denim Pants", brand: "Louis Vuitton", image_url: null, description: "2026 S/S 런웨이 피스. 하이웨이스트 와이드 실루엣" },
          { product_id: "prod-002", name: "Vintage Wash Denim Jacket", brand: "Acne Studios", image_url: null, description: "오버사이즈 핏의 클래식 데님 재킷. 미디엄 빈티지 워싱" },
          { product_id: "prod-003", name: "Low-Rise Straight Jeans", brand: "AGOLDE", image_url: null, description: "90년대 영감의 로우라이즈 스트레이트. 라이트 블루 워싱" }
        ] },
        { type: "divider", style: "ornament" },
        { type: "headline", text: "스타일링 팁: 데님 믹스 매치의 정석", level: 2 },
        { type: "body_text", paragraphs: [
          "1. 데님 온 데님은 톤 차이를 두는 것이 핵심. 상의는 다크 인디고, 하의는 라이트 블루로 대비를 줄 것.",
          "2. 데님 재킷 안에 실크나 새틴 소재의 블라우스를 매치하면 캐주얼과 포멀의 균형을 잡을 수 있다.",
          "3. 액세서리는 미니멀하게. 골드 체인 하나면 충분하다."
        ] },
        { type: "hashtag_bar", hashtags: ["뉴진스데님", "2026SS", "데님트렌드", "와이드데님", "데님온데님", "패션트렌드"] },
        { type: "credits", entries: [
          { role: "AI Editor", name: "decoded editorial" },
          { role: "Trend Research", name: "Gemini Search Grounding" },
          { role: "Layout", name: "Magazine Layout v1.0" }
        ] }
      ],
      created_at: "2026-02-25T10:00:00Z",
      metadata: [
        { key: "source", value: "gemini-2.5-flash" },
        { key: "revision_count", value: "1" }
      ]
    },
    review_summary: "Format: PASS. Hallucination: PASS. Fact Accuracy: PASS. Content Completeness: PASS. Overall: 잘 구성된 데님 트렌드 에디토리얼. 셀럽 레퍼런스와 상품 추천이 적절히 포함됨.",
    rejection_reason: null,
    admin_feedback: null,
    created_at: "2026-02-25T10:05:00Z",
    updated_at: "2026-02-25T10:05:00Z",
    published_at: null,
  },
  {
    id: "demo-002",
    thread_id: "thread-demo-002",
    status: "pending",
    title: "제니의 봄 레이어링: 시스루부터 트렌치까지",
    keyword: "제니 레이어링",
    layout_json: {
      schema_version: "1.0",
      title: "제니의 봄 레이어링: 시스루부터 트렌치까지",
      subtitle: "겹겹이 쌓는 스타일의 정석",
      keyword: "제니 레이어링",
      blocks: [
        { type: "hero", image_url: "https://placeholder.co/1200x675", overlay_title: "Layering Mastery", overlay_subtitle: "Spring 2026" },
        { type: "headline", text: "제니가 보여주는 봄 레이어링의 교과서", level: 1 },
        { type: "body_text", paragraphs: [
          "봄의 변덕스러운 날씨는 오히려 패션의 기회다. 제니는 샤넬 앰배서더답게 시스루 탑 위에 트위드 재킷을 걸치거나, 오버사이즈 트렌치코트 안에 니트 베스트를 레이어링하는 모습으로 '봄 레이어링의 정석'을 보여주고 있다.",
          "이번 시즌의 레이어링 키워드는 '투명함과 구조감의 공존'. 가벼운 시스루 소재와 구조적인 아우터의 대비가 핵심이다."
        ] },
        { type: "celeb_feature", celebs: [
          { celeb_id: "celeb-003", name: "제니", image_url: null, description: "샤넬 글로벌 앰배서더. 시스루 + 트위드 레이어링의 대표 아이콘" }
        ] },
        { type: "product_showcase", products: [
          { product_id: "prod-004", name: "Classic Trench Coat", brand: "Burberry", image_url: null, description: "헤리티지 개버딘 트렌치. 벨티드 웨이스트로 실루엣 강조" },
          { product_id: "prod-005", name: "Sheer Mesh Top", brand: "Dior", image_url: null, description: "도트 패턴 시스루 메쉬 탑. 이너 레이어링에 최적" }
        ] },
        { type: "divider", style: "line" },
        { type: "hashtag_bar", hashtags: ["제니패션", "봄레이어링", "시스루", "트렌치코트", "2026봄"] },
        { type: "credits", entries: [
          { role: "AI Editor", name: "decoded editorial" },
          { role: "Trend Research", name: "Gemini Search Grounding" }
        ] }
      ],
      created_at: "2026-02-25T11:00:00Z",
      metadata: []
    },
    review_summary: "Format: PASS. Hallucination: PASS. Fact Accuracy: PASS. Content Completeness: PASS.",
    rejection_reason: null,
    admin_feedback: null,
    created_at: "2026-02-25T11:05:00Z",
    updated_at: "2026-02-25T11:05:00Z",
    published_at: null,
  },
  {
    id: "demo-003",
    thread_id: "thread-demo-003",
    status: "approved",
    title: "차은우 × 프라다: 2026 남성 패션의 뉴 스탠다드",
    keyword: "차은우 프라다",
    layout_json: {
      schema_version: "1.0",
      title: "차은우 × 프라다: 2026 남성 패션의 뉴 스탠다드",
      keyword: "차은우 프라다",
      blocks: [
        { type: "hero", image_url: "https://placeholder.co/1200x675", overlay_title: "New Menswear Standard" },
        { type: "headline", text: "프라다가 선택한 남자, 차은우", level: 1 },
        { type: "body_text", paragraphs: [
          "차은우가 프라다 2026 S/S 캠페인의 아시아 얼굴이 되었다. 클래식한 테일러링에 현대적 감성을 더한 이번 컬렉션은 차은우의 단정하면서도 모던한 이미지와 완벽하게 맞아떨어진다.",
          "특히 슬림 핏 수트에 청키 더비 슈즈를 매치한 룩은 '스마트 캐주얼'의 새로운 기준을 제시한다."
        ] },
        { type: "celeb_feature", celebs: [
          { celeb_id: "celeb-004", name: "차은우", image_url: null, description: "프라다 2026 S/S 캠페인 모델. 클래식 테일러링의 아이콘" }
        ] },
        { type: "product_showcase", products: [
          { product_id: "prod-006", name: "Re-Nylon Slim Suit", brand: "Prada", image_url: null, description: "리사이클 나일론 소재의 슬림 핏 수트. 지속가능한 럭셔리" }
        ] },
        { type: "hashtag_bar", hashtags: ["차은우", "프라다", "남성패션", "2026SS"] },
        { type: "credits", entries: [{ role: "AI Editor", name: "decoded editorial" }] }
      ],
      created_at: "2026-02-24T09:00:00Z",
      metadata: []
    },
    review_summary: "All criteria passed.",
    rejection_reason: null,
    admin_feedback: "좋은 콘텐츠. 발행 승인.",
    created_at: "2026-02-24T09:05:00Z",
    updated_at: "2026-02-24T14:30:00Z",
    published_at: null,
  },
  {
    id: "demo-004",
    thread_id: "thread-demo-004",
    status: "rejected",
    title: "아이유의 빈티지 무드: 레트로 패션 가이드",
    keyword: "아이유 빈티지",
    layout_json: {
      schema_version: "1.0",
      title: "아이유의 빈티지 무드: 레트로 패션 가이드",
      keyword: "아이유 빈티지",
      blocks: [
        { type: "hero", image_url: "https://placeholder.co/1200x675", overlay_title: "Vintage Mood" },
        { type: "headline", text: "아이유와 함께하는 레트로 패션 여행", level: 1 },
        { type: "body_text", paragraphs: [
          "아이유가 최근 화보에서 선보인 70년대 영감의 빈티지 룩이 화제다. 플레어 팬츠와 자카드 블라우스의 조합은 레트로 패션의 정수를 보여준다."
        ] },
        { type: "divider", style: "space" },
        { type: "hashtag_bar", hashtags: ["아이유", "빈티지패션", "레트로"] },
        { type: "credits", entries: [{ role: "AI Editor", name: "decoded editorial" }] }
      ],
      created_at: "2026-02-23T15:00:00Z",
      metadata: []
    },
    review_summary: "Content Completeness: FAIL. 상품 추천과 셀럽 피처가 누락됨.",
    rejection_reason: "콘텐츠가 너무 짧고, 상품 추천 섹션과 셀럽 피처 블록이 빠져있습니다. 보완 후 재제출 바랍니다.",
    admin_feedback: null,
    created_at: "2026-02-23T15:05:00Z",
    updated_at: "2026-02-23T16:00:00Z",
    published_at: null,
  },
  {
    id: "demo-005",
    thread_id: "thread-demo-005",
    status: "pending",
    title: "2026 봄 컬러 트렌드: 버터 옐로우부터 라벤더까지",
    keyword: "봄 컬러 트렌드",
    layout_json: {
      schema_version: "1.0",
      title: "2026 봄 컬러 트렌드: 버터 옐로우부터 라벤더까지",
      keyword: "봄 컬러 트렌드",
      blocks: [
        { type: "hero", image_url: "https://placeholder.co/1200x675", overlay_title: "Color Forecast", overlay_subtitle: "Spring 2026" },
        { type: "headline", text: "이번 봄, 당신의 옷장을 물들일 5가지 컬러", level: 1 },
        { type: "body_text", paragraphs: [
          "팬톤이 선정한 2026 올해의 컬러 'Cosmic Latte'의 영향으로, 이번 봄은 부드러운 파스텔 톤이 지배한다.",
          "버터 옐로우, 라벤더, 민트 그린, 피치 핑크, 그리고 아이스 블루 — 다섯 가지 키 컬러를 중심으로 한 스타일링을 제안한다."
        ] },
        { type: "image_gallery", images: [
          { url: "https://placeholder.co/400x400", alt: "버터 옐로우", caption: "Butter Yellow" },
          { url: "https://placeholder.co/400x400", alt: "라벤더", caption: "Lavender" },
          { url: "https://placeholder.co/400x400", alt: "민트 그린", caption: "Mint Green" },
          { url: "https://placeholder.co/400x400", alt: "피치 핑크", caption: "Peach Pink" },
          { url: "https://placeholder.co/400x400", alt: "아이스 블루", caption: "Ice Blue" }
        ], layout_style: "carousel" },
        { type: "pull_quote", quote: "컬러는 감정의 언어다. 올 봄의 파스텔은 낙관과 부드러움을 말한다.", attribution: "Pantone Color Institute" },
        { type: "product_showcase", products: [
          { product_id: "prod-007", name: "Cashmere V-Neck Sweater (Butter)", brand: "COS", image_url: null, description: "버터 옐로우 캐시미어 니트. 봄 트랜지션 피스로 완벽" },
          { product_id: "prod-008", name: "Tailored Bermuda Shorts (Lavender)", brand: "AMI Paris", image_url: null, description: "라벤더 컬러 테일러드 버뮤다. 리넨 혼방 소재" }
        ] },
        { type: "divider", style: "ornament" },
        { type: "hashtag_bar", hashtags: ["봄컬러", "2026트렌드", "파스텔", "버터옐로우", "라벤더"] },
        { type: "credits", entries: [
          { role: "AI Editor", name: "decoded editorial" },
          { role: "Color Reference", name: "Pantone Color Institute" }
        ] }
      ],
      created_at: "2026-02-25T12:00:00Z",
      metadata: [{ key: "source", value: "gemini-2.5-flash" }]
    },
    review_summary: "Format: PASS. Hallucination: PASS. Fact Accuracy: PASS. Content Completeness: PASS. 컬러별 스타일링 제안이 명확하고 시즌 트렌드를 잘 반영함.",
    rejection_reason: null,
    admin_feedback: null,
    created_at: "2026-02-25T12:05:00Z",
    updated_at: "2026-02-25T12:05:00Z",
    published_at: null,
  },
];

// ---------------------------------------------------------------------------
// Query helpers
// ---------------------------------------------------------------------------

export function getDemoItems(status?: string): ContentItem[] {
  if (status) {
    return demoItems.filter((item) => item.status === status);
  }
  return demoItems;
}

export function getDemoItemById(id: string): ContentItem | undefined {
  return demoItems.find((item) => item.id === id);
}

export function approveDemoItem(id: string): ContentItem | undefined {
  const item = demoItems.find((i) => i.id === id);
  if (item) {
    item.status = "approved";
    item.updated_at = new Date().toISOString();
  }
  return item;
}

export function rejectDemoItem(
  id: string,
  reason: string,
): ContentItem | undefined {
  const item = demoItems.find((i) => i.id === id);
  if (item) {
    item.status = "rejected";
    item.rejection_reason = reason;
    item.updated_at = new Date().toISOString();
  }
  return item;
}
