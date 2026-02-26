import type { BodyTextBlock, DesignSpec } from "@/lib/types";

interface BodyTextBlockProps {
  block: BodyTextBlock;
  designSpec?: DesignSpec;
}

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

const BODY_FONT_STYLE = { fontFamily: "var(--font-noto-sans-kr), 'Noto Sans KR', sans-serif" };
const PLAYFAIR_STYLE = { fontFamily: "var(--font-playfair), Georgia, serif" };

function DropCap({
  char,
  color,
  sizeClass = "text-[3.5rem] leading-[0.8]",
}: {
  char: string;
  color: string;
  sizeClass?: string;
}) {
  return (
    <span
      className={`float-left mr-3 mt-1 font-bold ${sizeClass}`}
      style={{ ...PLAYFAIR_STYLE, color }}
      data-drop-cap
    >
      {char}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Variant: single_column (default / current behavior)
// ---------------------------------------------------------------------------

function SingleColumn({ block, designSpec }: BodyTextBlockProps) {
  const showDropCap = designSpec?.drop_cap !== false;
  const dropCapColor = designSpec?.color_palette?.primary ?? "#1a1a2e";

  return (
    <div style={BODY_FONT_STYLE}>
      {block.paragraphs.map((text, i) => {
        const shouldDropCap = i === 0 && showDropCap && text.length > 0;

        if (shouldDropCap) {
          return (
            <p key={i} className="mb-6 text-[17px] leading-[1.8] text-gray-800 last:mb-0">
              <DropCap char={text.charAt(0)} color={dropCapColor} />
              {text.slice(1)}
            </p>
          );
        }

        return (
          <p key={i} className="mb-6 text-[17px] leading-[1.8] text-gray-800 last:mb-0">
            {text}
          </p>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant: two_column
// ---------------------------------------------------------------------------

function TwoColumn({ block, designSpec }: BodyTextBlockProps) {
  const showDropCap = designSpec?.drop_cap !== false;
  const dropCapColor = designSpec?.color_palette?.primary ?? "#1a1a2e";

  return (
    <div className="columns-1 md:columns-2 gap-8" style={BODY_FONT_STYLE}>
      {block.paragraphs.map((text, i) => {
        const shouldDropCap = i === 0 && showDropCap && text.length > 0;

        if (shouldDropCap) {
          return (
            <p key={i} className="mb-6 text-[17px] leading-[1.8] text-gray-800 break-inside-avoid last:mb-0">
              <DropCap char={text.charAt(0)} color={dropCapColor} />
              {text.slice(1)}
            </p>
          );
        }

        return (
          <p key={i} className="mb-6 text-[17px] leading-[1.8] text-gray-800 break-inside-avoid last:mb-0">
            {text}
          </p>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant: three_column
// ---------------------------------------------------------------------------

function ThreeColumn({ block, designSpec }: BodyTextBlockProps) {
  const showDropCap = designSpec?.drop_cap !== false;
  const dropCapColor = designSpec?.color_palette?.primary ?? "#1a1a2e";

  return (
    <div className="columns-1 md:columns-2 lg:columns-3 gap-6" style={BODY_FONT_STYLE}>
      {block.paragraphs.map((text, i) => {
        const shouldDropCap = i === 0 && showDropCap && text.length > 0;

        if (shouldDropCap) {
          return (
            <p key={i} className="mb-6 text-[17px] leading-[1.8] text-gray-800 break-inside-avoid last:mb-0">
              <DropCap char={text.charAt(0)} color={dropCapColor} />
              {text.slice(1)}
            </p>
          );
        }

        return (
          <p key={i} className="mb-6 text-[17px] leading-[1.8] text-gray-800 break-inside-avoid last:mb-0">
            {text}
          </p>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant: wide -- larger text, more line height
// ---------------------------------------------------------------------------

function Wide({ block, designSpec }: BodyTextBlockProps) {
  const showDropCap = designSpec?.drop_cap !== false;
  const dropCapColor = designSpec?.color_palette?.primary ?? "#1a1a2e";

  return (
    <div style={BODY_FONT_STYLE}>
      {block.paragraphs.map((text, i) => {
        const shouldDropCap = i === 0 && showDropCap && text.length > 0;

        if (shouldDropCap) {
          return (
            <p key={i} className="mb-6 text-lg leading-[2] text-gray-800 last:mb-0">
              <DropCap char={text.charAt(0)} color={dropCapColor} />
              {text.slice(1)}
            </p>
          );
        }

        return (
          <p key={i} className="mb-6 text-lg leading-[2] text-gray-800 last:mb-0">
            {text}
          </p>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant: narrow_centered -- centered text, spacious feel
// ---------------------------------------------------------------------------

function NarrowCentered({ block, designSpec }: BodyTextBlockProps) {
  const showDropCap = designSpec?.drop_cap !== false;
  const dropCapColor = designSpec?.color_palette?.primary ?? "#1a1a2e";

  return (
    <div style={BODY_FONT_STYLE}>
      {block.paragraphs.map((text, i) => {
        const shouldDropCap = i === 0 && showDropCap && text.length > 0;

        if (shouldDropCap) {
          return (
            <p key={i} className="mb-6 text-lg leading-[2] text-center text-gray-800 last:mb-0">
              <DropCap char={text.charAt(0)} color={dropCapColor} />
              {text.slice(1)}
            </p>
          );
        }

        return (
          <p key={i} className="mb-6 text-lg leading-[2] text-center text-gray-800 last:mb-0">
            {text}
          </p>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant: drop_cap_accent -- oversized drop cap with decorative border
// ---------------------------------------------------------------------------

function DropCapAccent({ block, designSpec }: BodyTextBlockProps) {
  const accentColor = designSpec?.color_palette?.accent ?? "#e94560";
  const dropCapColor = designSpec?.color_palette?.accent ?? "#e94560";

  return (
    <div style={BODY_FONT_STYLE}>
      {block.paragraphs.map((text, i) => {
        const isFirst = i === 0;

        if (isFirst && text.length > 0) {
          return (
            <p
              key={i}
              className="mb-6 text-[17px] leading-[1.8] text-gray-800 border-l-2 pl-6 last:mb-0"
              style={{ borderColor: accentColor }}
            >
              <DropCap
                char={text.charAt(0)}
                color={dropCapColor}
                sizeClass="text-[5rem] leading-[0.7]"
              />
              {text.slice(1)}
            </p>
          );
        }

        return (
          <p key={i} className="mb-6 text-[17px] leading-[1.8] text-gray-800 last:mb-0">
            {text}
          </p>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function BodyTextBlockComponent({ block, designSpec }: BodyTextBlockProps) {
  const paragraphs = block.paragraphs ?? [];
  if (paragraphs.length === 0) return null;

  const variant = block.layout_variant ?? "single_column";

  switch (variant) {
    case "two_column":
      return <TwoColumn block={block} designSpec={designSpec} />;
    case "three_column":
      return <ThreeColumn block={block} designSpec={designSpec} />;
    case "wide":
      return <Wide block={block} designSpec={designSpec} />;
    case "narrow_centered":
      return <NarrowCentered block={block} designSpec={designSpec} />;
    case "drop_cap_accent":
      return <DropCapAccent block={block} designSpec={designSpec} />;
    case "single_column":
    default:
      return <SingleColumn block={block} designSpec={designSpec} />;
  }
}
