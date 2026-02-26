import { Card, CardContent } from "@/components/ui/card";
import { MagazineImage } from "@/components/magazine-image";
import type { ProductShowcaseBlock, ProductItem, DesignSpec } from "@/lib/types";

interface ProductShowcaseBlockProps {
  block: ProductShowcaseBlock;
  designSpec?: DesignSpec;
}

export function ProductShowcaseBlockComponent({ block, designSpec }: ProductShowcaseBlockProps) {
  const products = block.products ?? [];

  if (products.length === 0) {
    return null;
  }

  const variant = block.layout_variant ?? "grid";

  switch (variant) {
    case "full_width_row":
      return (
        <div className="flex gap-6 overflow-x-auto pb-3">
          {products.map((product, i) => (
            <div key={i} className="flex-none w-48">
              <MagazineImage
                src={product.image_url || ""}
                alt={product.name}
                aspectRatio="1/1"
                className="rounded-lg"
                gradientFrom={designSpec?.color_palette?.primary}
                gradientTo={designSpec?.color_palette?.accent}
              />
              <p className="mt-2 font-semibold text-sm">{product.name ?? "Untitled"}</p>
              {product.brand && (
                <p className="text-xs text-muted-foreground">{product.brand}</p>
              )}
            </div>
          ))}
        </div>
      );

    case "featured_plus_grid":
      return (
        <div className="space-y-4">
          {/* Featured first product */}
          {products.length > 0 && (
            <div className="overflow-hidden rounded-lg">
              <MagazineImage
                src={products[0].image_url || ""}
                alt={products[0].name}
                aspectRatio="16/10"
                className="rounded-lg"
                gradientFrom={designSpec?.color_palette?.primary}
                gradientTo={designSpec?.color_palette?.accent}
              />
              <div className="mt-3">
                <p className="text-2xl font-semibold">{products[0].name ?? "Untitled"}</p>
                {products[0].brand && (
                  <p className="text-sm text-muted-foreground">{products[0].brand}</p>
                )}
                {products[0].description && (
                  <p className="mt-1 text-sm text-gray-600">{products[0].description}</p>
                )}
              </div>
            </div>
          )}
          {/* Remaining products in grid */}
          {products.length > 1 && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              {products.slice(1).map((product, i) => (
                <ProductCard key={i} product={product} designSpec={designSpec} />
              ))}
            </div>
          )}
        </div>
      );

    case "minimal_list":
      return (
        <div className="divide-y">
          {products.map((product, i) => (
            <div key={i} className="flex justify-between items-center py-4">
              <div>
                <p className="font-semibold">{product.name ?? "Untitled"}</p>
                {product.brand && (
                  <p className="text-sm text-muted-foreground">{product.brand}</p>
                )}
              </div>
              {product.description && (
                <p className="text-sm text-gray-500 text-right max-w-[50%]">{product.description}</p>
              )}
            </div>
          ))}
        </div>
      );

    case "lookbook":
      return (
        <div className="space-y-0">
          {products.map((product, i) => {
            const isEven = i % 2 === 0;
            return (
              <div key={i} className="grid grid-cols-1 md:grid-cols-5 gap-0">
                {/* Image side */}
                <div className={`md:col-span-3 ${!isEven ? "md:order-2" : ""}`}>
                  <MagazineImage
                    src={product.image_url || ""}
                    alt={product.name}
                    aspectRatio="4/3"
                    className="rounded-none"
                    gradientFrom={designSpec?.color_palette?.primary}
                    gradientTo={designSpec?.color_palette?.accent}
                  />
                </div>
                {/* Text side */}
                <div className={`md:col-span-2 flex items-center p-8 ${!isEven ? "md:order-1" : ""}`}>
                  <div>
                    <p className="text-xl font-semibold">{product.name ?? "Untitled"}</p>
                    {product.brand && (
                      <p className="mt-1 text-sm text-muted-foreground">{product.brand}</p>
                    )}
                    {product.description && (
                      <p className="mt-3 text-sm text-gray-600 leading-relaxed">{product.description}</p>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      );

    case "carousel_cards":
      return (
        <div className="flex gap-4 overflow-x-auto snap-x snap-mandatory pb-3">
          {products.map((product, i) => (
            <Card key={i} className="flex-none w-72 snap-start group overflow-hidden py-0 hover:shadow-lg transition-shadow duration-300">
              <div className="overflow-hidden">
                <div className="group-hover:scale-105 transition-transform duration-300">
                  <MagazineImage
                    src={product.image_url || ""}
                    alt={product.name}
                    aspectRatio="3/4"
                    className="rounded-none"
                    gradientFrom={designSpec?.color_palette?.primary}
                    gradientTo={designSpec?.color_palette?.accent}
                  />
                </div>
              </div>
              <CardContent className="p-4">
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

    case "grid":
    default:
      return (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {products.map((product, i) => (
            <ProductCard key={i} product={product} designSpec={designSpec} />
          ))}
        </div>
      );
  }
}

/** Wraps children in an anchor tag if link_url is present */
function LinkWrapper({ href, children }: { href?: string | null; children: React.ReactNode }) {
  if (href) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className="block">
        {children}
      </a>
    );
  }
  return <>{children}</>;
}

/** Reusable product card (used in grid + featured_plus_grid) */
function ProductCard({ product, designSpec }: { product: ProductItem; designSpec?: DesignSpec }) {
  return (
    <LinkWrapper href={product.link_url}>
      <Card className={`group overflow-hidden py-0 ${product.link_url ? "cursor-pointer hover:shadow-lg transition-shadow" : ""}`}>
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
    </LinkWrapper>
  );
}
