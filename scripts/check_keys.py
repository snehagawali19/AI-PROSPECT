"""Minimal live check of each external integration (1 call each). Prints OK / FAIL per service.
Costs: 1 Serper credit, 1 YouTube search unit, 2 tiny LLM calls.

Usage:  python -m scripts.check_keys      (or: docker compose run --rm api python -m scripts.check_keys)
"""
import asyncio
import httpx
from pydantic import BaseModel
from app.config import get_settings, is_configured
from app.services.llm_service import make_provider

class Ping(BaseModel):
    ok: bool

async def check_serper(client, s):
    r = await client.post("https://google.serper.dev/search", json={"q": "fastapi", "num": 1},
                          headers={"X-API-KEY": s.serper_api_key}, timeout=15)
    r.raise_for_status()
    return f"{len(r.json().get('organic', []))} result(s)"

async def check_youtube(client, s):
    r = await client.get("https://www.googleapis.com/youtube/v3/search",
                         params={"part": "snippet", "type": "channel", "q": "python", "maxResults": 1,
                                 "key": s.youtube_api_key}, timeout=15)
    r.raise_for_status()
    return f"{len(r.json().get('items', []))} channel(s)"

async def check_llm(provider, model):
    res = await make_provider(provider, model).generate(
        "Reply by calling the tool / returning JSON with ok=true.", "ping", Ping)
    return f"ok={Ping.model_validate(res.data).ok} tokens_in={res.input_tokens} tokens_out={res.output_tokens}"

async def main() -> None:
    s = get_settings()
    async with httpx.AsyncClient() as client:
        checks = [
            ("Serper", is_configured(s.serper_api_key), lambda: check_serper(client, s)),
            ("YouTube", is_configured(s.youtube_api_key), lambda: check_youtube(client, s)),
            (f"LLM primary {s.primary_provider}/{s.primary_model}", is_configured(s.primary_model),
             lambda: check_llm(s.primary_provider, s.primary_model)),
            (f"LLM fallback {s.fallback_provider}/{s.fallback_model}", is_configured(s.fallback_model),
             lambda: check_llm(s.fallback_provider, s.fallback_model)),
        ]
        for name, configured, fn in checks:
            if not configured:
                print(f"[SKIP] {name}: not configured in .env")
                continue
            try:
                print(f"[ OK ] {name}: {await fn()}")
            except Exception as e:
                print(f"[FAIL] {name}: {type(e).__name__}: {str(e)[:200]}")

if __name__ == "__main__":
    asyncio.run(main())
