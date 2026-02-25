import { Card, CardContent } from "@/components/ui/card";
import type { ProductShowcaseBlock } from "@/lib/types";

export function ProductShowcaseBlockComponent({ block }: { block: ProductShowcaseBlock }) {
  const products = block.products ?? [];

  if (products.length === 0) {
    return null;
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
      {products.map((product, i) => (
        <Card key={i} className="overflow-hidden py-0">
          <div className="flex aspect-square items-center justify-center bg-blue-100 text-sm text-blue-600">
            Product Photo
          </div>
          <CardContent className="p-3">
            <p className="font-bold">{product.name ?? "Untitled"}</p>
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
