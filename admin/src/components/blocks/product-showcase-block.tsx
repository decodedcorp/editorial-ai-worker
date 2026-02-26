import { Card, CardContent } from "@/components/ui/card";
import { MagazineImage } from "@/components/magazine-image";
import type { ProductShowcaseBlock, DesignSpec } from "@/lib/types";

interface ProductShowcaseBlockProps {
  block: ProductShowcaseBlock;
  designSpec?: DesignSpec;
}

export function ProductShowcaseBlockComponent({ block, designSpec }: ProductShowcaseBlockProps) {
  const products = block.products ?? [];

  if (products.length === 0) {
    return null;
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
      {products.map((product, i) => (
        <Card key={i} className="group overflow-hidden py-0">
          <div className="overflow-hidden">
            <div className="group-hover:scale-105 transition-transform duration-300">
              <MagazineImage
                src={product.image_url || ""}
                alt={product.name}
                aspectRatio="1/1"
                className="rounded-none"
                gradientFrom={designSpec?.color_palette?.primary}
                gradientTo={designSpec?.color_palette?.accent}
              />
            </div>
          </div>
          <CardContent className="p-3">
            <p className="font-semibold">{product.name ?? "Untitled"}</p>
            {product.brand && (
              <p className="text-sm text-muted-foreground">{product.brand}</p>
            )}
            {product.description && (
              <p className="mt-1 text-xs text-gray-600">{product.description}</p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
