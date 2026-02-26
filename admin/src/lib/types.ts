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
// Animation type for per-block GSAP animations (AI-decided)
// ---------------------------------------------------------------------------

export type AnimationType =
  | "fade-up"
  | "fade-in"
  | "slide-left"
  | "slide-right"
  | "scale-in"
  | "parallax"
  | "none";

// ---------------------------------------------------------------------------
// Block types -- discriminated union on `type` field
// ---------------------------------------------------------------------------

export interface HeroBlock {
  type: "hero";
  image_url: string;
  overlay_title?: string | null;
  overlay_subtitle?: string | null;
  animation?: AnimationType | null;
}

export interface HeadlineBlock {
  type: "headline";
  text: string;
  level: 1 | 2 | 3;
  animation?: AnimationType | null;
}

export interface BodyTextBlock {
  type: "body_text";
  paragraphs: string[];
  animation?: AnimationType | null;
}

export interface ImageGalleryBlock {
  type: "image_gallery";
  images: ImageItem[];
  layout_style: "grid" | "carousel" | "masonry";
  animation?: AnimationType | null;
}

export interface PullQuoteBlock {
  type: "pull_quote";
  quote: string;
  attribution?: string | null;
  animation?: AnimationType | null;
}

export interface ProductShowcaseBlock {
  type: "product_showcase";
  products: ProductItem[];
  animation?: AnimationType | null;
}

export interface CelebFeatureBlock {
  type: "celeb_feature";
  celebs: CelebItem[];
  animation?: AnimationType | null;
}

export interface DividerBlock {
  type: "divider";
  style: "line" | "space" | "ornament";
  animation?: AnimationType | null;
}

export interface HashtagBarBlock {
  type: "hashtag_bar";
  hashtags: string[];
  animation?: AnimationType | null;
}

export interface CreditsBlock {
  type: "credits";
  entries: CreditEntry[];
  animation?: AnimationType | null;
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
  design_spec?: DesignSpec | null;
}

// ---------------------------------------------------------------------------
// Design Spec types -- mirrors src/editorial_ai/models/design_spec.py
// ---------------------------------------------------------------------------

export interface FontPairing {
  headline_font: string;
  body_font: string;
  accent_font?: string | null;
}

export interface ColorPalette {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  text: string;
  muted: string;
}

export interface DesignSpec {
  font_pairing: FontPairing;
  color_palette: ColorPalette;
  layout_density: "compact" | "normal" | "spacious";
  mood: string;
  hero_aspect_ratio: string;
  drop_cap: boolean;
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

// ---------------------------------------------------------------------------
// Pipeline trigger types
// ---------------------------------------------------------------------------

export interface TriggerRequest {
  seed_keyword: string;
  category?: string;
  tone?: string;
  style?: string;
  target_celeb?: string;
  target_brand?: string;
  mode?: "ai_curation" | "db_source" | "ai_db_search";
  selected_posts?: string[];
  selected_celebs?: string[];
  selected_products?: string[];
}

// ---------------------------------------------------------------------------
// DB Source search types
// ---------------------------------------------------------------------------

export interface SolutionItem {
  solution_id: string;
  title: string;
  thumbnail_url: string | null;
  link_type: string | null;
  original_url: string | null;
  brand: string | null;
  category: string | null;
  material: string[] | null;
  origin: string | null;
  keywords: string[];
}

export interface PostSource {
  id: string;
  image_url: string | null;
  media_type: string | null;
  title: string;
  artist_name: string;
  group_name: string;
  context: string;
  view_count: number;
  trending_score: number;
  solutions: SolutionItem[];
}

export interface CelebSource {
  id: string;
  name: string;
  name_en: string | null;
  category: string | null;
  profile_image_url: string | null;
  description: string | null;
  tags: string[] | null;
}

export interface ProductSource {
  id: string;
  name: string;
  brand: string | null;
  category: string | null;
  price: number | null;
  image_url: string | null;
  description: string | null;
  product_url: string | null;
  tags: string[] | null;
}

export interface SourceSearchResponse {
  posts?: PostSource[];
  celebs?: CelebSource[];
  products?: ProductSource[];
}

export interface TriggerResponse {
  thread_id: string;
  message: string;
}

export interface PipelineStatus {
  thread_id: string;
  pipeline_status: string;
  error_log: string[];
  has_draft: boolean;
}

// ---------------------------------------------------------------------------
// Observability log types -- mirrors src/editorial_ai/api/schemas.py
// ---------------------------------------------------------------------------

export interface TokenUsageItem {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  model_name: string | null;
}

export interface NodeRunLog {
  node_name: string;
  status: "success" | "error" | "skipped";
  started_at: string;   // ISO datetime string
  ended_at: string;     // ISO datetime string
  duration_ms: number;
  token_usage: TokenUsageItem[];
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  prompt_chars: number;
  error_type: string | null;
  error_message: string | null;
  input_state: Record<string, unknown> | null;
  output_state: Record<string, unknown> | null;
}

export interface PipelineRunSummary {
  thread_id: string;
  node_count: number;
  total_duration_ms: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  status: string;
  started_at: string | null;
  ended_at: string | null;
}

export interface LogsResponse {
  content_id: string;
  thread_id: string;
  runs: NodeRunLog[];
  summary: PipelineRunSummary | null;
}

// ---------------------------------------------------------------------------
// Content item with pipeline summary (enriched by BFF list proxy)
// ---------------------------------------------------------------------------

export interface PipelineSummaryFields {
  total_duration_ms: number | null;
  estimated_cost_usd: number | null;
  retry_count: number;
}

export interface ContentItemWithSummary extends ContentItem {
  pipeline_summary: PipelineSummaryFields | null;
}

export interface ContentListWithSummaryResponse {
  items: ContentItemWithSummary[];
  total: number;
}
