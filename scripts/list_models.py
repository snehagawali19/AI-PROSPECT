"""Print the model IDs your keys can actually use, so you can set PRIMARY_MODEL / FALLBACK_MODEL in .env.

Usage (from the project root, with .env filled in):
    python -m scripts.list_models
    docker compose run --rm api python -m scripts.list_models
"""
import asyncio
from app.config import get_settings, is_configured

async def anthropic_models(key: str) -> list[str]:
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=key)
    page = await client.models.list(limit=100)
    return [m.id for m in page.data]

async def gemini_models(key: str) -> list[str]:
    from google import genai
    client = genai.Client(api_key=key)
    names = []
    async for m in await client.aio.models.list():
        actions = getattr(m, "supported_actions", None) or []
        if not actions or "generateContent" in actions:
            names.append(m.name.removeprefix("models/"))
    return names

async def main() -> None:
    s = get_settings()
    for label, key, fn in (("Anthropic", s.anthropic_api_key, anthropic_models),
                           ("Gemini", s.gemini_api_key, gemini_models)):
        print(f"\n== {label} ==")
        if not is_configured(key):
            print("  key not configured in .env — skipped")
            continue
        try:
            for model_id in await fn(key):
                print(" ", model_id)
        except Exception as e:
            print(f"  could not list models: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
