// ---------------------------------------------------------------------------
// Supporting types
// ---------------------------------------------------------------------------

export interface KeyValuePair {
  key: string;
  value: string;
}

export interface ImageItem {
  url: string;
  alt?: string | null;
  caption?: string | null;
}

export interface ProductItem {
  product_id?: string | null;
  name: string;
  brand?: string | null;
  image_url?: string | null;
  description?: string | null;
}

export interface CelebItem {
  celeb_id?: string | null;
  name: string;
  image_url?: string | null;
  description?: string | null;
}

export interface CreditEntry {
  role: string;
  name: string;
}

// ---------------------------------------------------------------------------
// Block types -- discriminated union on `type` field
// ---------------------------------------------------------------------------

export interface HeroBlock {
  type: "hero";
  image_url: string;
  overlay_title?: string | null;
  overlay_subtitle?: string | null;
}

export interface HeadlineBlock {
  type: "headline";
  text: string;
  level: 1 | 2 | 3;
}

export interface BodyTextBlock {
  type: "body_text";
  paragraphs: string[];
}

export interface ImageGalleryBlock {
  type: "image_gallery";
  images: ImageItem[];
  layout_style: "grid" | "carousel" | "masonry";
}

export interface PullQuoteBlock {
  type: "pull_quote";
  quote: string;
  attribution?: string | null;
}

export interface ProductShowcaseBlock {
  type: "product_showcase";
  products: ProductItem[];
}

export interface CelebFeatureBlock {
  type: "celeb_feature";
  celebs: CelebItem[];
}

export interface DividerBlock {
  type: "divider";
  style: "line" | "space" | "ornament";
}

export interface HashtagBarBlock {
  type: "hashtag_bar";
  hashtags: string[];
}

export interface CreditsBlock {
  type: "credits";
  entries: CreditEntry[];
}

// ---------------------------------------------------------------------------
// Discriminated union of all block types
// ---------------------------------------------------------------------------

export type LayoutBlock =
  | HeroBlock
  | HeadlineBlock
  | BodyTextBlock
  | ImageGalleryBlock
  | PullQuoteBlock
  | ProductShowcaseBlock
  | CelebFeatureBlock
  | DividerBlock
  | HashtagBarBlock
  | CreditsBlock;

// ---------------------------------------------------------------------------
// MagazineLayout -- mirrors src/editorial_ai/models/layout.py
// ---------------------------------------------------------------------------

export interface MagazineLayout {
  schema_version: string;
  title: string;
  subtitle?: string | null;
  keyword: string;
  blocks: LayoutBlock[];
  created_at?: string | null;
  metadata?: KeyValuePair[];
}

// ---------------------------------------------------------------------------
// Content API types -- mirrors src/editorial_ai/api/schemas.py
// ---------------------------------------------------------------------------

export interface ContentItem {
  id: string;
  thread_id: string;
  status: string;
  title: string;
  keyword: string;
  layout_json: MagazineLayout;
  review_summary?: string | null;
  rejection_reason?: string | null;
  admin_feedback?: string | null;
  created_at: string;
  updated_at: string;
  published_at?: string | null;
}

export interface ContentListResponse {
  items: ContentItem[];
  total: number;
}

// ---------------------------------------------------------------------------
// Request types
// ---------------------------------------------------------------------------

export interface ApproveRequest {
  feedback?: string;
}

export interface RejectRequest {
  reason: string;
}
