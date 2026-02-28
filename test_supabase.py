import asyncio
from editorial_ai.services.content_service import list_contents
from editorial_ai.config import settings

async def main():
    try:
        print(f"URL: {settings.supabase_url}")
        res = await list_contents()
        print(f"Success: {len(res)} items")
    except Exception as e:
        print(f"Error type: {type(e)}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
