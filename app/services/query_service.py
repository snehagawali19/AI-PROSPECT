"""Section 1: NL query understanding (LLM) + deterministic, platform-specific query generation."""
from pathlib import Path
from app.errors import InvalidQuery
from app.schemas import Intent
from app.services.llm_service import structured
from app.utils.cache import TTLCache

SYSTEM = (Path(__file__).resolve().parent.parent / "prompts" / "intent_system.txt").read_text(encoding="utf-8")
_cache = TTLCache(24 * 3600)

async def parse_intent(query: str, usage: dict) -> Intent:
    key = " ".join(query.lower().split())
    if (hit := _cache.get(key)):
        usage["intent_cached"] = True
        return hit
    intent = await structured(SYSTEM, f"<request>{query}</request>", Intent, usage)
    if not intent.is_valid_query or not intent.audience.strip():
        raise InvalidQuery("Could not identify a target audience in the query.",
                           {"hint": "e.g. 'Restaurant owners in Dubai UAE'"})
    _cache.set(key, intent)
    return intent

def _or(terms: list[str], limit: int = 4) -> str:
    t = [x.strip() for x in dict.fromkeys(terms) if x and x.strip()][:limit]
    if not t:
        return ""
    q = [f'"{x}"' for x in t]
    return q[0] if len(q) == 1 else "(" + " OR ".join(q) + ")"

def location_terms(i: Intent) -> list[str]:
    base = [i.location.city] if i.location.city else []
    return list(dict.fromkeys(i.location_aliases + base)) or [i.location.country or ""]

def topic_terms(i: Intent) -> str:
    """Hobby audiences → interest synonyms. Business/professional → role AND category."""
    if i.target_type == "individual" or not i.role_keywords:
        return _or(i.interest_keywords or [i.interest or i.audience])
    cat = i.business_category or i.interest
    return f'{_or(i.role_keywords, 3)} {_or([cat] if cat else i.interest_keywords, 2)}'.strip()

SITE = {   # platform → site: filter + exclusions of non-profile URL types
    "LinkedIn":  "site:linkedin.com/in",
    "Instagram": "site:instagram.com -inurl:/p/ -inurl:/reel/ -inurl:/explore/",
    "Facebook":  "site:facebook.com -inurl:/groups/ -inurl:/posts/ -inurl:/events/ -inurl:/videos/",
    "X":         "(site:x.com OR site:twitter.com) -inurl:/status/",
    "Threads":   "(site:threads.com OR site:threads.net)",
}

def build_site_query(i: Intent, platform: str) -> str:
    q = f'{SITE[platform]} {topic_terms(i)} {_or(location_terms(i), 3)}'
    return " ".join(q.split())

def build_youtube_query(i: Intent) -> str:
    kw = (i.interest_keywords or [i.interest or i.audience])[0]
    return f"{kw} {i.location.city or i.location.country or ''}".strip()

def build_places_query(i: Intent) -> str | None:
    if i.target_type == "individual":
        return None
    cat = i.business_category or i.interest
    return f"{cat} in {i.location.city or i.location.state}, {i.location.country}" if cat else None

def build_web_query(i: Intent) -> str | None:
    if i.target_type == "individual":
        return None
    excl = "-site:linkedin.com -site:facebook.com -site:instagram.com -site:x.com -site:youtube.com"
    return " ".join(f'{topic_terms(i)} {_or(location_terms(i), 3)} {excl}'.split())

def gl(i: Intent) -> str:
    return (i.location.country_code or "us").lower()
