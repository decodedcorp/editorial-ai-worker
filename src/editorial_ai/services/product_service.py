"""Read-only service functions for the products table."""

from editorial_ai.models.product import Product
from editorial_ai.services.supabase_client import get_supabase_client


async def get_product_by_id(product_id: str) -> Product | None:
    """Fetch a single product by ID. Returns None if not found."""
    client = await get_supabase_client()
    response = await (
        client.table("products").select("*").eq("id", product_id).maybe_single().execute()
    )
    if response is None or response.data is None:
        return None
    return Product.model_validate(response.data)


async def search_products(query: str, *, limit: int = 10) -> list[Product]:
    """Search products by name (case-insensitive partial match)."""
    client = await get_supabase_client()
    response = await (
        client.table("products").select("*").ilike("name", f"%{query}%").limit(limit).execute()
    )
    return [Product.model_validate(row) for row in response.data]


async def search_products_multi(queries: list[str], *, limit: int = 10) -> list[Product]:
    """Search products across name, brand, description for multiple queries.

    Uses Supabase or_() with PostgREST syntax for multi-column ilike matching.
    Results from all queries are deduplicated by ID, preserving first occurrence order.
    """
    if not queries:
        return []
    client = await get_supabase_client()
    all_results: list[Product] = []
    for query in queries:
        pattern = f"%{query}%"
        response = await (
            client.table("products")
            .select("*")
            .or_(f"name.ilike.{pattern},brand.ilike.{pattern},description.ilike.{pattern}")
            .limit(limit)
            .execute()
        )
        all_results.extend(Product.model_validate(row) for row in response.data)
    return _deduplicate_by_id(all_results)


def _deduplicate_by_id(items: list[Product]) -> list[Product]:
    """Remove duplicate products by ID, preserving first occurrence order."""
    seen: set[str] = set()
    result: list[Product] = []
    for item in items:
        if item.id not in seen:
            seen.add(item.id)
            result.append(item)
    return result
