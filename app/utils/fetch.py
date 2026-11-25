"""SSRF-safe page fetch (from Test 1): every redirect hop re-validated, size/time/content-type caps."""
from urllib.parse import urljoin
import httpx
from app.errors import AppError, SiteBlocked, SiteTimeout, SiteUnreachable, UnsupportedContent
from app.utils.validators import assert_public_host

UA = "Mozilla/5.0 (compatible; ProspectDiscoveryBot/1.0; +https://github.com/<you>/ai-prospect-discovery)"

async def safe_fetch(client: httpx.AsyncClient, url: str, max_bytes: int = 1_000_000, hops: int = 4) -> tuple[str, str]:
    for _ in range(hops):
        await assert_public_host(url)
        try:
            async with client.stream("GET", url) as r:
                if r.is_redirect:
                    url = urljoin(url, r.headers.get("location", "")); continue
                if r.status_code in (401, 403, 429, 503):
                    raise SiteBlocked("Blocked or restricted.", {"upstream_status": r.status_code})
                if r.status_code >= 400:
                    raise SiteUnreachable("Upstream error.", {"upstream_status": r.status_code})
                if "html" not in r.headers.get("content-type", ""):
                    raise UnsupportedContent("Not HTML.")
                buf = bytearray()
                async for chunk in r.aiter_bytes():
                    buf += chunk
                    if len(buf) > max_bytes:
                        break
                return bytes(buf).decode(r.encoding or "utf-8", errors="replace"), str(r.url)
        except httpx.TimeoutException:
            raise SiteTimeout("Timed out.")
        except httpx.HTTPError as e:
            raise SiteUnreachable("Connection failed.", {"reason": type(e).__name__})
    raise SiteUnreachable("Too many redirects.")


# ---------------- robots.txt (prospects' own websites only) ----------------
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from app.utils.cache import TTLCache

ROBOTS_UA = "ProspectDiscoveryBot"
_robots_cache = TTLCache(3600)

async def allowed_by_robots(client: httpx.AsyncClient, url: str) -> bool:
    """Fetch and honour /robots.txt (cached 1h per host). A missing robots.txt means 'allowed';
    401/403 on robots.txt means 'disallow everything' (same rule as Python's RobotFileParser.read)."""
    parts = urlsplit(url)
    root = f"{parts.scheme}://{parts.netloc}"
    rp = _robots_cache.get(root)
    if rp is None:
        rp = RobotFileParser()
        try:
            await assert_public_host(root + "/robots.txt")
            r = await client.get(root + "/robots.txt", timeout=5)
            if r.status_code in (401, 403):
                rp.disallow_all = True
                rp.modified()
            elif r.status_code == 200 and len(r.content) < 500_000:
                rp.parse(r.text.splitlines())
            else:
                rp.parse([])
        except Exception:
            rp.parse([])
        _robots_cache.set(root, rp)
    return rp.can_fetch(ROBOTS_UA, url)
