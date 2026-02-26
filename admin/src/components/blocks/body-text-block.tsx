import type { BodyTextBlock, DesignSpec } from "@/lib/types";

interface BodyTextBlockProps {
  block: BodyTextBlock;
  designSpec?: DesignSpec;
}

export function BodyTextBlockComponent({ block, designSpec }: BodyTextBlockProps) {
  const paragraphs = block.paragraphs ?? [];

  if (paragraphs.length === 0) {
    return null;
  }

  const showDropCap = designSpec?.drop_cap !== false;
  const dropCapColor = designSpec?.color_palette?.primary ?? "#1a1a2e";

  return (
    <div style={{ fontFamily: "var(--font-noto-sans-kr), 'Noto Sans KR', sans-serif" }}>
      {paragraphs.map((text, i) => {
        const isFirst = i === 0;
        const shouldDropCap = isFirst && showDropCap && text.length > 0;

        if (shouldDropCap) {
          const firstChar = text.charAt(0);
          const rest = text.slice(1);

          return (
            <p
              key={i}
              className="mb-6 text-[17px] leading-[1.8] text-gray-800 last:mb-0"
            >
              <span
                className="float-left text-[3.5rem] leading-[0.8] mr-3 mt-1 font-bold"
                style={{
                  fontFamily: "var(--font-playfair), Georgia, serif",
                  color: dropCapColor,
                }}
                data-drop-cap
              >
                {firstChar}
              </span>
              {rest}
            </p>
          );
        }

        return (
          <p
            key={i}
            className="mb-6 text-[17px] leading-[1.8] text-gray-800 last:mb-0"
          >
            {text}
          </p>
        );
      })}
    </div>
  );
}
