"""Authorized search clients with per-request budget, retry on 429/5xx, and caching."""
import asyncio, hashlib, json, random
from dataclasses import dataclass, field
import httpx
from app.config import get_settings, is_configured
from app.errors import BudgetExceeded
from app.schemas import Intent
from app.utils.cache import TTLCache

_cache = TTLCache(get_settings().cache_ttl_s)

class RateLimited(Exception): ...
class QuotaExhausted(Exception): ...
class NotConfigured(Exception): ...

@dataclass
class Ctx:
    """Per-request context handed to every platform adapter."""
    client: httpx.AsyncClient
    intent: Intent
    serp_calls: int = 0
    site_fetches: int = 0
    usage: dict = field(default_factory=dict)

    def take_serp(self):
        if self.serp_calls >= get_settings().max_serp_calls:
            raise BudgetExceeded("Per-request search budget reached.")
        self.serp_calls += 1

async def _post_json(client, url, payload, headers, retries=2):
    for attempt in range(retries + 1):
        r = await client.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code == 429 or r.status_code >= 500:
            if attempt == retries:
                raise RateLimited(f"{url} -> {r.status_code}") if r.status_code == 429 else httpx.HTTPStatusError("upstream", request=r.request, response=r)
            wait = float(r.headers.get("retry-after", 0) or (2 ** attempt + random.random()))
            await asyncio.sleep(min(wait, 5)); continue
        if r.status_code in (401, 403):
            raise QuotaExhausted(f"{url} -> {r.status_code}")
        r.raise_for_status()
        return r.json()

async def _get_json(client, url, params, retries=2):
    for attempt in range(retries + 1):
        r = await client.get(url, params=params, timeout=10)
        if r.status_code == 403 and "quota" in r.text.lower():
            raise QuotaExhausted("YouTube quota exhausted")
        if r.status_code == 429 or r.status_code >= 500:
            if attempt == retries:
                raise RateLimited(url)
            await asyncio.sleep(2 ** attempt + random.random()); continue
        r.raise_for_status()
        return r.json()

def _key(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()

async def serper(ctx: Ctx, endpoint: str, q: str, gl: str, num: int | None = None) -> dict:
    """endpoint: 'search' | 'places'. Results cached for cache_ttl_s (also saves credits during demos)."""
    s = get_settings()
    if not is_configured(s.serper_api_key):
        raise NotConfigured("SERPER_API_KEY not set")
    k = _key("serper", endpoint, q, gl, num)
    if (hit := _cache.get(k)) is not None:
        return hit
    ctx.take_serp()
    payload = {"q": q, "gl": gl}
    if num:
        payload["num"] = num
    data = await _post_json(ctx.client, f"https://google.serper.dev/{endpoint}", payload,
                            {"X-API-KEY": s.serper_api_key, "Content-Type": "application/json"})
    _cache.set(k, data)
    return data

async def youtube(ctx: Ctx, method: str, params: dict) -> dict:
    s = get_settings()
    if not is_configured(s.youtube_api_key):
        raise NotConfigured("YOUTUBE_API_KEY not set")
    k = _key("yt", method, params)
    if (hit := _cache.get(k)) is not None:
        return hit
    data = await _get_json(ctx.client, f"https://www.googleapis.com/youtube/v3/{method}",
                           {**params, "key": s.youtube_api_key})
    _cache.set(k, data)
    return data
